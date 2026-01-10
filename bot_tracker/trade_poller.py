"""
Real-time trade poller for target wallets.
Uses Polymarket Data API for wallet trades.
"""

import asyncio
import aiohttp
import re
from typing import List, Set, Dict, Callable, Awaitable, Optional
from datetime import datetime

from .config import (
    POLYMARKET_DATA_API, GAMMA_API, TARGET_WALLETS,
    TRADE_POLL_INTERVAL, REQUEST_TIMEOUT,
    MARKET_SLUGS_PATTERN, MARKET_FILTER_ENABLED, BUY_ONLY
)
from .models import TradeEvent


class TradePoller:
    """Polls Polymarket Data API for wallet trades."""

    def __init__(self, on_new_trades: Callable[[List[TradeEvent]], Awaitable[None]]):
        """
        Initialize the trade poller.

        Args:
            on_new_trades: Async callback when new trades are detected
        """
        self.on_new_trades = on_new_trades
        self.seen_trade_ids: Set[str] = set()
        self.last_trade_timestamp: Dict[str, int] = {}  # wallet -> timestamp
        self.running = False
        # Cache for condition_id -> market metadata
        self.market_cache: Dict[str, dict] = {}

    async def _fetch_market_by_condition(
        self,
        session: aiohttp.ClientSession,
        condition_id: str
    ) -> Optional[dict]:
        """Fetch market metadata from Gamma API by condition ID."""
        if condition_id in self.market_cache:
            return self.market_cache[condition_id]

        try:
            async with session.get(
                f"{GAMMA_API}/markets",
                params={"condition_id": condition_id},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    markets = await resp.json()
                    if markets:
                        market = markets[0] if isinstance(markets, list) else markets
                        self.market_cache[condition_id] = market
                        return market
        except Exception as e:
            print(f"Error fetching market for condition {condition_id[:20]}...: {e}")
        return None

    async def _poll_wallet_trades(
        self,
        session: aiohttp.ClientSession,
        wallet: str
    ) -> List[dict]:
        """Fetch recent trades for a wallet from Polymarket Data API."""
        params = {
            "user": wallet,
            "limit": 100,
            "takerOnly": "false",  # Get all trades, not just taker
        }

        # Only get BUY trades if configured
        if BUY_ONLY:
            params["side"] = "BUY"

        try:
            async with session.get(
                f"{POLYMARKET_DATA_API}/trades",
                params=params,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"Error fetching trades: {resp.status}")
                    return []
        except Exception as e:
            print(f"Error polling trades for {wallet[:10]}...: {e}")
            return []

    def _parse_trade(
        self,
        raw: dict,
        wallet: str,
        wallet_name: str
    ) -> Optional[TradeEvent]:
        """Parse raw Polymarket trade into TradeEvent."""
        # Create unique ID from transaction hash + asset
        trade_id = f"{raw.get('transactionHash', '')}:{raw.get('asset', '')}"

        # Parse timestamp (ISO format or unix)
        ts = raw.get("timestamp")
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                timestamp = int(dt.timestamp())
            except:
                timestamp = int(datetime.now().timestamp())
        else:
            timestamp = int(ts) if ts else int(datetime.now().timestamp())

        # Get market slug from response
        market_slug = raw.get("slug", "")
        market_question = raw.get("title", "")

        # Apply market filter
        if MARKET_FILTER_ENABLED and market_slug:
            if not re.match(MARKET_SLUGS_PATTERN, market_slug):
                return None

        return TradeEvent(
            id=trade_id,
            tx_hash=raw.get("transactionHash", ""),
            timestamp=timestamp,
            wallet=wallet,
            wallet_name=wallet_name,
            role="taker",  # Polymarket API returns from taker perspective
            side=raw.get("side", "BUY"),
            outcome=raw.get("outcome", "Unknown"),
            shares=float(raw.get("size", 0)),
            usdc=float(raw.get("size", 0)) * float(raw.get("price", 0)),
            price=float(raw.get("price", 0)),
            fee=0,  # Fee not provided in this API
            market_slug=market_slug,
            market_question=market_question
        )

    async def poll_all_wallets(self) -> List[TradeEvent]:
        """Poll all target wallets for new trades."""
        new_trades = []

        async with aiohttp.ClientSession() as session:
            # Fetch trades from all wallets concurrently
            tasks = [
                self._poll_wallet_trades(session, wallet)
                for wallet in TARGET_WALLETS.keys()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for wallet, result in zip(TARGET_WALLETS.keys(), results):
                if isinstance(result, Exception):
                    print(f"Error polling wallet {wallet[:10]}...: {result}")
                    continue

                wallet_name = TARGET_WALLETS[wallet]

                for raw in result:
                    # Parse trade
                    parsed = self._parse_trade(raw, wallet, wallet_name)
                    if not parsed:
                        continue

                    # Skip already seen trades (use ID only, not timestamp)
                    if parsed.id in self.seen_trade_ids:
                        continue

                    self.seen_trade_ids.add(parsed.id)
                    new_trades.append(parsed)

        # Sort by timestamp
        new_trades.sort(key=lambda t: t.timestamp)

        # Callback with new trades
        if new_trades and self.on_new_trades:
            await self.on_new_trades(new_trades)

        return new_trades

    async def run(self):
        """Main polling loop."""
        self.running = True
        print(f"Trade poller started. Tracking {len(TARGET_WALLETS)} wallets...")
        print(f"  Poll interval: {TRADE_POLL_INTERVAL}s")
        print(f"  BUY only: {BUY_ONLY}")
        print(f"  Market filter: {MARKET_FILTER_ENABLED} ({MARKET_SLUGS_PATTERN})")

        while self.running:
            try:
                trades = await self.poll_all_wallets()
                if trades:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Detected {len(trades)} new trades")
                    for t in trades:
                        print(f"  {t.side} {t.outcome} {t.shares:.2f} @ ${t.price:.3f} ({t.market_slug})")
            except Exception as e:
                print(f"Polling error: {e}")

            await asyncio.sleep(TRADE_POLL_INTERVAL)

    def stop(self):
        """Stop the polling loop."""
        self.running = False
