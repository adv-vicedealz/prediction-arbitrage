"""
Market discovery - finds active/upcoming 15-minute BTC/ETH markets.
"""

import asyncio
import aiohttp
import re
import time
from typing import List, Set, Optional
from datetime import datetime, timezone

from .config import GAMMA_API, REQUEST_TIMEOUT, MARKET_SLUGS_PATTERN
from .models import MarketContext
from .market_context import MarketContextFetcher, parse_iso_datetime


class MarketDiscovery:
    """
    Discovers new 15-minute BTC/ETH markets from Gamma API.

    Since the Gamma API doesn't support slug_contains for these markets,
    we calculate expected timestamps and query by specific slug.
    """

    def __init__(self, market_fetcher: MarketContextFetcher):
        self.market_fetcher = market_fetcher
        self.discovered_slugs: Set[str] = set()
        self.running = False

    def _generate_market_slugs(self, lookback_periods: int = 4, lookahead_periods: int = 2) -> List[str]:
        """Generate expected market slugs based on current time.

        15-min markets have timestamps rounded to 15-min intervals (900 seconds).
        """
        now = int(time.time())
        interval = 900  # 15 minutes in seconds
        base_ts = (now // interval) * interval

        slugs = []
        for asset in ["btc", "eth"]:
            # Look back and ahead
            for offset in range(-lookback_periods, lookahead_periods + 1):
                ts = base_ts + (offset * interval)
                slugs.append(f"{asset}-updown-15m-{ts}")

        return slugs

    async def discover_markets(self) -> List[MarketContext]:
        """Find all active/upcoming 15-min BTC/ETH markets."""
        new_markets = []

        # Generate expected slugs based on current time
        expected_slugs = self._generate_market_slugs()

        async with aiohttp.ClientSession() as session:
            for slug in expected_slugs:
                # Skip if already discovered
                if slug in self.discovered_slugs:
                    continue

                # Try to fetch this specific market
                market = await self._fetch_market_by_slug(session, slug)
                if not market:
                    continue

                # Build full context
                try:
                    context = await self.market_fetcher.build_context(session, market)
                    self.discovered_slugs.add(slug)
                    new_markets.append(context)
                    print(f"[Discovery] New market: {slug} (closed: {market.get('closed', False)})")
                except Exception as e:
                    print(f"[Discovery] Error building context for {slug}: {e}")

        return new_markets

    async def _fetch_market_by_slug(
        self,
        session: aiohttp.ClientSession,
        slug: str
    ) -> Optional[dict]:
        """Fetch a specific market by slug."""
        try:
            async with session.get(
                f"{GAMMA_API}/markets",
                params={"slug": slug},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    markets = await resp.json()
                    if markets:
                        return markets[0] if isinstance(markets, list) else markets
        except Exception as e:
            pass  # Silently ignore - market might not exist yet
        return None

    async def discover_recent_resolved(self, hours_back: int = 24) -> List[MarketContext]:
        """
        Find recently resolved markets for backfill.
        Useful for catching up on markets that resolved while we were offline.
        """
        resolved_markets = []

        # Calculate how many 15-min periods to look back
        periods_back = int((hours_back * 60) / 15)  # e.g., 24h = 96 periods

        # Generate slugs for past periods
        now = int(time.time())
        interval = 900  # 15 minutes
        base_ts = (now // interval) * interval

        async with aiohttp.ClientSession() as session:
            for asset in ["btc", "eth"]:
                for i in range(1, periods_back + 1):
                    ts = base_ts - (i * interval)
                    slug = f"{asset}-updown-15m-{ts}"

                    # Skip if already discovered
                    if slug in self.discovered_slugs:
                        continue

                    # Try to fetch this market
                    market = await self._fetch_market_by_slug(session, slug)
                    if not market:
                        continue

                    # Only include closed markets
                    if not market.get("closed", False):
                        continue

                    try:
                        context = await self.market_fetcher.build_context(session, market)
                        self.discovered_slugs.add(slug)
                        resolved_markets.append(context)

                        hours_ago = i * 0.25  # Each period is 15 min = 0.25 hours
                        print(f"[Discovery] Recent resolved: {slug} ({hours_ago:.1f}h ago)")
                    except Exception as e:
                        print(f"[Discovery] Error building context for {slug}: {e}")

        return resolved_markets

    async def run(self, interval: int = 30):
        """Main loop - periodically discover new markets."""
        self.running = True
        print(f"[Discovery] Started (interval: {interval}s)")

        while self.running:
            try:
                new_markets = await self.discover_markets()
                if new_markets:
                    print(f"[Discovery] Found {len(new_markets)} new markets")
            except Exception as e:
                print(f"[Discovery] Error: {e}")

            await asyncio.sleep(interval)

    def stop(self):
        """Stop the discovery loop."""
        self.running = False

    def get_discovered_count(self) -> int:
        """Get number of markets discovered."""
        return len(self.discovered_slugs)

    def mark_as_discovered(self, slug: str):
        """Mark a market as already discovered (e.g., from storage)."""
        self.discovered_slugs.add(slug)
