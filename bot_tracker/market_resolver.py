"""
Market resolver - fetches complete trade data after markets resolve.
Guarantees 100% trade capture by querying after trading stops.
"""

import asyncio
import aiohttp
import re
from dataclasses import dataclass
from typing import Dict, Set, List, Optional, Callable, Awaitable
from datetime import datetime, timezone
import time

from .config import (
    POLYMARKET_DATA_API, GAMMA_API, REQUEST_TIMEOUT,
    TARGET_WALLETS, MARKET_SLUGS_PATTERN
)
from .models import TradeEvent, MarketContext


@dataclass
class PendingMarket:
    """Market waiting to be resolved."""
    slug: str
    condition_id: str
    end_timestamp: int  # Unix timestamp when market ends
    question: str = ""


class MarketResolver:
    """
    Fetches complete trade data after markets resolve.

    Instead of polling during trading (which can miss trades),
    we wait until the market closes, then fetch ALL trades
    using the conditionId filter for guaranteed completeness.
    """

    def __init__(
        self,
        on_trades_fetched: Callable[[str, List[TradeEvent], Optional[str]], Awaitable[None]],
        resolution_delay_seconds: int = 120  # Wait 2 min after market ends
    ):
        """
        Args:
            on_trades_fetched: Callback when trades are fetched for a market.
                              Args: (market_slug, trades, winning_outcome)
            resolution_delay_seconds: How long to wait after market ends before fetching
        """
        self.on_trades_fetched = on_trades_fetched
        self.resolution_delay = resolution_delay_seconds

        self.pending_markets: Dict[str, PendingMarket] = {}  # slug -> PendingMarket
        self.completed_markets: Set[str] = set()
        self.running = False

    def add_market(self, slug: str, condition_id: str, end_timestamp: int, question: str = ""):
        """Register a market to fetch when it resolves."""
        if slug in self.completed_markets:
            return  # Already processed

        if slug not in self.pending_markets:
            self.pending_markets[slug] = PendingMarket(
                slug=slug,
                condition_id=condition_id,
                end_timestamp=end_timestamp,
                question=question
            )
            print(f"[Resolver] Tracking market: {slug} (ends at {datetime.fromtimestamp(end_timestamp)})")

    def add_market_from_context(self, context: MarketContext):
        """Register a market from a MarketContext object."""
        if not context.end_date:
            return

        end_ts = int(context.end_date.timestamp())
        self.add_market(
            slug=context.slug,
            condition_id=context.condition_id,
            end_timestamp=end_ts,
            question=context.question
        )

    async def _fetch_trades_for_market(
        self,
        session: aiohttp.ClientSession,
        market: PendingMarket
    ) -> List[TradeEvent]:
        """Fetch ALL trades for a resolved market using conditionId + user."""
        all_trades = []

        for wallet, wallet_name in TARGET_WALLETS.items():
            offset = 0
            wallet_trades = []

            while True:
                params = {
                    "conditionId": market.condition_id,
                    "user": wallet,
                    "limit": 500,
                    "offset": offset
                }

                try:
                    async with session.get(
                        f"{POLYMARKET_DATA_API}/trades",
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as resp:
                        if resp.status != 200:
                            print(f"[Resolver] Error fetching trades: {resp.status}")
                            break
                        raw_trades = await resp.json()
                except Exception as e:
                    print(f"[Resolver] Error: {e}")
                    break

                if not raw_trades:
                    break

                # Parse trades
                for raw in raw_trades:
                    trade = self._parse_trade(raw, wallet, wallet_name, market.slug)
                    if trade:
                        wallet_trades.append(trade)

                if len(raw_trades) < 500:
                    break
                offset += 500

            if wallet_trades:
                print(f"[Resolver] {market.slug}: {len(wallet_trades)} trades for {wallet_name}")
                all_trades.extend(wallet_trades)

        # Sort by timestamp
        all_trades.sort(key=lambda t: t.timestamp)
        return all_trades

    def _parse_trade(
        self,
        raw: dict,
        wallet: str,
        wallet_name: str,
        market_slug: str
    ) -> Optional[TradeEvent]:
        """Parse raw trade data into TradeEvent."""
        trade_id = f"{raw.get('transactionHash', '')}:{raw.get('asset', '')}"

        # Parse timestamp
        ts = raw.get("timestamp")
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                timestamp = int(dt.timestamp())
            except:
                timestamp = int(time.time())
        else:
            timestamp = int(ts) if ts else int(time.time())

        return TradeEvent(
            id=trade_id,
            tx_hash=raw.get("transactionHash", ""),
            timestamp=timestamp,
            wallet=wallet,
            wallet_name=wallet_name,
            role="taker",
            side=raw.get("side", "BUY"),
            outcome=raw.get("outcome", "Unknown"),
            shares=float(raw.get("size", 0)),
            usdc=float(raw.get("size", 0)) * float(raw.get("price", 0)),
            price=float(raw.get("price", 0)),
            fee=0,
            market_slug=market_slug,
            market_question=raw.get("title", "")
        )

    async def _fetch_market_resolution(
        self,
        session: aiohttp.ClientSession,
        market: PendingMarket
    ) -> Optional[str]:
        """Fetch the winning outcome for a resolved market."""
        try:
            async with session.get(
                f"{GAMMA_API}/markets",
                params={"slug": market.slug},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    markets = await resp.json()
                    if markets:
                        market_data = markets[0] if isinstance(markets, list) else markets
                        if market_data.get("closed"):
                            outcome_prices = market_data.get("outcomePrices", "[]")
                            outcomes = market_data.get("outcomes", "[]")

                            if isinstance(outcome_prices, str):
                                import json
                                outcome_prices = json.loads(outcome_prices)
                            if isinstance(outcomes, str):
                                import json
                                outcomes = json.loads(outcomes)

                            for i, price in enumerate(outcome_prices):
                                if float(price) == 1.0 and i < len(outcomes):
                                    return outcomes[i]
        except Exception as e:
            print(f"[Resolver] Error fetching resolution for {market.slug}: {e}")
        return None

    async def check_and_resolve(self):
        """Check for markets that have ended and fetch their trades."""
        now = int(time.time())

        for slug, market in list(self.pending_markets.items()):
            # Wait for market to end + delay buffer
            if now <= market.end_timestamp + self.resolution_delay:
                continue

            print(f"[Resolver] Processing resolved market: {slug}")

            async with aiohttp.ClientSession() as session:
                # Fetch all trades
                trades = await self._fetch_trades_for_market(session, market)

                # Fetch winning outcome
                winning_outcome = await self._fetch_market_resolution(session, market)

                print(f"[Resolver] {slug}: {len(trades)} total trades, winner: {winning_outcome}")

                # Callback with results
                if self.on_trades_fetched:
                    await self.on_trades_fetched(slug, trades, winning_outcome)

            # Mark as completed
            self.completed_markets.add(slug)
            del self.pending_markets[slug]

    async def run(self, check_interval: int = 30):
        """Main loop - periodically check for resolved markets."""
        self.running = True
        print(f"[Resolver] Started (delay: {self.resolution_delay}s, interval: {check_interval}s)")

        while self.running:
            try:
                await self.check_and_resolve()
            except Exception as e:
                print(f"[Resolver] Error: {e}")

            await asyncio.sleep(check_interval)

    def stop(self):
        """Stop the resolver loop."""
        self.running = False

    def get_pending_count(self) -> int:
        """Get number of markets waiting for resolution."""
        return len(self.pending_markets)

    def get_completed_count(self) -> int:
        """Get number of markets that have been processed."""
        return len(self.completed_markets)

    def is_completed(self, slug: str) -> bool:
        """Check if a market has been processed."""
        return slug in self.completed_markets
