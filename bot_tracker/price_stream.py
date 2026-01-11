"""
Real-time price stream from Polymarket WebSocket.
Connects to wss://ws-subscriptions-clob.polymarket.com/ws/market
"""

import asyncio
import json
from typing import Dict, Set, Callable, Awaitable, Optional
from datetime import datetime
from dataclasses import dataclass

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from .config import POLYMARKET_WS_URL


@dataclass
class PriceUpdate:
    """Real-time price update from WebSocket."""
    asset_id: str
    market_slug: str
    outcome: str  # "Up" or "Down"
    price: float
    best_bid: float
    best_ask: float
    timestamp: int


@dataclass
class TradeExecution:
    """Trade execution event from WebSocket."""
    asset_id: str
    market_slug: str
    outcome: str
    price: float
    size: float
    side: str  # "BUY" or "SELL"
    timestamp: int


class PriceStream:
    """Streams real-time prices from Polymarket WebSocket."""

    def __init__(
        self,
        on_price_update: Optional[Callable[[PriceUpdate], Awaitable[None]]] = None,
        on_trade: Optional[Callable[[TradeExecution], Awaitable[None]]] = None
    ):
        self.on_price_update = on_price_update
        self.on_trade = on_trade
        self.subscribed_assets: Set[str] = set()
        self.asset_metadata: Dict[str, dict] = {}  # asset_id -> {market_slug, outcome}
        self.running = False
        self.ws = None
        self.latest_prices: Dict[str, PriceUpdate] = {}  # asset_id -> latest price
        self.last_save_time: Dict[str, float] = {}  # asset_id -> last save timestamp
        self.save_interval = 1.0  # Only save prices every 1 second per asset

    def add_asset(self, asset_id: str, market_slug: str, outcome: str):
        """Add an asset to track."""
        self.subscribed_assets.add(asset_id)
        self.asset_metadata[asset_id] = {
            "market_slug": market_slug,
            "outcome": outcome
        }
        # Subscribe immediately if already connected
        if self.ws:
            asyncio.create_task(self.subscribe([asset_id]))

    def remove_asset(self, asset_id: str):
        """Remove an asset from tracking (for cleanup of resolved markets)."""
        self.subscribed_assets.discard(asset_id)
        self.asset_metadata.pop(asset_id, None)
        self.latest_prices.pop(asset_id, None)
        self.last_save_time.pop(asset_id, None)

    async def subscribe(self, asset_ids: list):
        """Subscribe to price updates for assets."""
        if not self.ws:
            return

        message = {
            "type": "market",
            "assets_ids": asset_ids  # Note: Polymarket API uses "assets_ids" (plural)
        }

        await self.ws.send(json.dumps(message))
        print(f"Subscribed to {len(asset_ids)} assets")

    async def handle_message(self, data: dict):
        """Handle incoming WebSocket message."""
        event_type = data.get("event_type")

        if event_type == "price_change":
            await self._handle_price_change(data)
        elif event_type == "last_trade_price":
            await self._handle_trade(data)
        elif event_type == "book":
            await self._handle_book(data)

    async def _handle_price_change(self, data: dict):
        """Handle price change event."""
        import time
        current_time = time.time()

        for change in data.get("price_changes", []):
            asset_id = change.get("asset_id")
            if asset_id not in self.asset_metadata:
                continue

            meta = self.asset_metadata[asset_id]
            update = PriceUpdate(
                asset_id=asset_id,
                market_slug=meta["market_slug"],
                outcome=meta["outcome"],
                price=float(change.get("price", 0)),
                best_bid=float(change.get("best_bid", 0)),
                best_ask=float(change.get("best_ask", 0)),
                timestamp=int(data.get("timestamp", 0)) // 1000  # ms to seconds
            )

            # Always update in-memory latest price
            self.latest_prices[asset_id] = update

            # Only save to storage if enough time has passed (throttle)
            last_save = self.last_save_time.get(asset_id, 0)
            if current_time - last_save >= self.save_interval:
                self.last_save_time[asset_id] = current_time
                if self.on_price_update:
                    await self.on_price_update(update)

    async def _handle_trade(self, data: dict):
        """Handle trade execution event."""
        asset_id = data.get("asset_id")
        if asset_id not in self.asset_metadata:
            return

        meta = self.asset_metadata[asset_id]
        trade = TradeExecution(
            asset_id=asset_id,
            market_slug=meta["market_slug"],
            outcome=meta["outcome"],
            price=float(data.get("price", 0)),
            size=float(data.get("size", 0)),
            side=data.get("side", ""),
            timestamp=int(data.get("timestamp", 0)) // 1000
        )

        if self.on_trade:
            await self.on_trade(trade)

    async def _handle_book(self, data: dict):
        """Handle orderbook snapshot."""
        import time
        current_time = time.time()

        asset_id = data.get("asset_id")
        if asset_id not in self.asset_metadata:
            return

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        best_bid = max((float(b["price"]) for b in bids), default=0)
        best_ask = min((float(a["price"]) for a in asks), default=0)
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0

        meta = self.asset_metadata[asset_id]
        update = PriceUpdate(
            asset_id=asset_id,
            market_slug=meta["market_slug"],
            outcome=meta["outcome"],
            price=mid_price,
            best_bid=best_bid,
            best_ask=best_ask,
            timestamp=int(data.get("timestamp", 0)) // 1000
        )

        # Always update in-memory latest price
        self.latest_prices[asset_id] = update

        # Only save to storage if enough time has passed (throttle)
        last_save = self.last_save_time.get(asset_id, 0)
        if current_time - last_save >= self.save_interval:
            self.last_save_time[asset_id] = current_time
            if self.on_price_update:
                await self.on_price_update(update)

    def get_latest_price(self, asset_id: str) -> Optional[PriceUpdate]:
        """Get the latest price for an asset."""
        return self.latest_prices.get(asset_id)

    def get_market_prices(self, market_slug: str) -> dict:
        """Get latest prices for a market (both Up and Down)."""
        prices = {}
        for asset_id, update in self.latest_prices.items():
            if update.market_slug == market_slug:
                prices[update.outcome.lower()] = {
                    "price": update.price,
                    "best_bid": update.best_bid,
                    "best_ask": update.best_ask,
                    "timestamp": update.timestamp
                }
        return prices

    async def connect(self):
        """Connect to WebSocket and maintain connection."""
        if not WEBSOCKETS_AVAILABLE:
            print("WebSocket not available: pip install websockets")
            return

        self.running = True
        reconnect_delay = 1

        while self.running:
            try:
                print(f"Connecting to Polymarket WebSocket...")
                async with websockets.connect(POLYMARKET_WS_URL) as ws:
                    self.ws = ws
                    print(f"Connected to {POLYMARKET_WS_URL}")
                    reconnect_delay = 1  # Reset on successful connect

                    # Subscribe to tracked assets
                    if self.subscribed_assets:
                        await self.subscribe(list(self.subscribed_assets))

                    # Listen for messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            # First message after subscribe is a list (orderbook snapshot)
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        await self.handle_message(item)
                            else:
                                await self.handle_message(data)
                        except json.JSONDecodeError:
                            print(f"Invalid JSON: {message[:100]}")
                        except Exception as e:
                            print(f"Error handling message: {e}")

            except Exception as e:
                print(f"WebSocket error: {e}")
                self.ws = None

            if self.running:
                print(f"Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30)

    async def run(self):
        """Start the price stream."""
        await self.connect()

    def stop(self):
        """Stop the price stream."""
        self.running = False
        if self.ws:
            asyncio.create_task(self.ws.close())
