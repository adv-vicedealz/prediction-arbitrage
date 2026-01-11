"""
Real-time price stream from Polymarket WebSocket.
"""

import asyncio
import json
import time
from typing import Dict, Set, Optional, Callable, Awaitable

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from ..config import WS_URL, PRICE_SAVE_INTERVAL
from ..database import Database
from ..logger import setup_logger

log = setup_logger(__name__)


class PriceStream:
    """
    Streams real-time prices from Polymarket WebSocket.

    Connects to wss://ws-subscriptions-clob.polymarket.com/ws/market
    """

    def __init__(self, db: Database):
        self.db = db
        self.running = False
        self.connected = False
        self.ws = None

        # Subscription tracking
        self.subscribed_assets: Set[str] = set()
        self.asset_metadata: Dict[str, Dict] = {}  # asset_id -> {market_slug, outcome}

        # Throttling
        self.last_save_time: Dict[str, float] = {}

    def subscribe(self, token_id: str, market_slug: str, outcome: str):
        """Add an asset to track."""
        if not token_id:
            return

        self.subscribed_assets.add(token_id)
        self.asset_metadata[token_id] = {
            "market_slug": market_slug,
            "outcome": outcome
        }

        # Subscribe immediately if connected
        if self.ws and self.connected:
            asyncio.create_task(self._send_subscribe([token_id]))

        log.debug(f"Subscribed to price: {token_id[:20]} ({market_slug})")

    def unsubscribe(self, token_id: str):
        """Remove an asset from tracking."""
        self.subscribed_assets.discard(token_id)
        self.asset_metadata.pop(token_id, None)
        self.last_save_time.pop(token_id, None)
        log.debug(f"Unsubscribed from price: {token_id[:20] if token_id else ''}")

    def get_status(self) -> Dict:
        """Get stream status."""
        return {
            "connected": self.connected,
            "running": self.running,
            "subscribed_assets": len(self.subscribed_assets),
            "assets": list(self.subscribed_assets)[:10]  # First 10 for display
        }

    async def run(self):
        """Start the price stream."""
        if not WEBSOCKETS_AVAILABLE:
            log.error("websockets package not installed")
            return

        self.running = True
        reconnect_delay = 1

        while self.running:
            try:
                log.info(f"Connecting to Polymarket WebSocket: {WS_URL}")

                async with websockets.connect(WS_URL) as ws:
                    self.ws = ws
                    self.connected = True
                    reconnect_delay = 1  # Reset on success
                    log.info("WebSocket connected")

                    # Subscribe to all tracked assets
                    if self.subscribed_assets:
                        await self._send_subscribe(list(self.subscribed_assets))

                    # Listen for messages
                    async for message in ws:
                        try:
                            await self._handle_message(message)
                        except Exception as e:
                            log.error(f"Message handling error: {e}")

            except Exception as e:
                log.error(f"WebSocket error: {e}")
                self.connected = False
                self.ws = None

            if self.running:
                log.info(f"Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30)

    def stop(self):
        """Stop the price stream."""
        self.running = False
        self.connected = False
        if self.ws:
            asyncio.create_task(self.ws.close())

    async def _send_subscribe(self, asset_ids: list):
        """Send subscription message."""
        if not self.ws or not asset_ids:
            return

        message = {
            "type": "market",
            "assets_ids": asset_ids  # Note: Polymarket uses "assets_ids" (plural)
        }

        try:
            await self.ws.send(json.dumps(message))
            log.info(f"Subscribed to {len(asset_ids)} assets")
        except Exception as e:
            log.error(f"Subscribe error: {e}")

    async def _handle_message(self, raw_message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            return

        # First message after subscribe can be a list (orderbook snapshot)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    await self._process_event(item)
        else:
            await self._process_event(data)

    async def _process_event(self, data: Dict):
        """Process a single event."""
        event_type = data.get("event_type")

        if event_type == "price_change":
            await self._handle_price_change(data)
        elif event_type == "book":
            await self._handle_book(data)
        # Ignore other event types

    async def _handle_price_change(self, data: Dict):
        """Handle price change event."""
        current_time = time.time()

        for change in data.get("price_changes", []):
            asset_id = change.get("asset_id")
            if asset_id not in self.asset_metadata:
                continue

            # Throttle: only save every PRICE_SAVE_INTERVAL seconds per asset
            last_save = self.last_save_time.get(asset_id, 0)
            if current_time - last_save < PRICE_SAVE_INTERVAL:
                continue

            meta = self.asset_metadata[asset_id]
            price_data = {
                "timestamp": int(data.get("timestamp", 0)) // 1000,  # ms to sec
                "market_slug": meta["market_slug"],
                "outcome": meta["outcome"],
                "price": float(change.get("price", 0)),
                "best_bid": float(change.get("best_bid", 0)),
                "best_ask": float(change.get("best_ask", 0))
            }

            self.db.save_price(price_data)
            self.last_save_time[asset_id] = current_time

    async def _handle_book(self, data: Dict):
        """Handle orderbook snapshot."""
        current_time = time.time()
        asset_id = data.get("asset_id")

        if asset_id not in self.asset_metadata:
            return

        # Throttle
        last_save = self.last_save_time.get(asset_id, 0)
        if current_time - last_save < PRICE_SAVE_INTERVAL:
            return

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        best_bid = max((float(b["price"]) for b in bids), default=0)
        best_ask = min((float(a["price"]) for a in asks), default=0)
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0

        meta = self.asset_metadata[asset_id]
        price_data = {
            "timestamp": int(data.get("timestamp", 0)) // 1000,
            "market_slug": meta["market_slug"],
            "outcome": meta["outcome"],
            "price": mid_price,
            "best_bid": best_bid,
            "best_ask": best_ask
        }

        self.db.save_price(price_data)
        self.last_save_time[asset_id] = current_time
