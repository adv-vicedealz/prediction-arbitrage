"""
Market discovery - finds active/upcoming 15-minute BTC/ETH markets.
"""

import asyncio
import aiohttp
import re
from typing import List, Set, Optional
from datetime import datetime, timezone

from .config import GAMMA_API, REQUEST_TIMEOUT, MARKET_SLUGS_PATTERN
from .models import MarketContext
from .market_context import MarketContextFetcher, parse_iso_datetime


class MarketDiscovery:
    """
    Discovers new 15-minute BTC/ETH markets from Gamma API.

    Polls for markets matching the pattern (btc|eth)-updown-15m-*
    and tracks them for the resolver to process after they end.
    """

    def __init__(self, market_fetcher: MarketContextFetcher):
        self.market_fetcher = market_fetcher
        self.discovered_slugs: Set[str] = set()
        self.running = False

    async def discover_markets(self) -> List[MarketContext]:
        """Find all active/upcoming 15-min BTC/ETH markets."""
        new_markets = []

        async with aiohttp.ClientSession() as session:
            # Search for BTC and ETH 15-min markets
            for asset in ["btc", "eth"]:
                markets = await self._fetch_markets_for_asset(session, asset)
                for market in markets:
                    slug = market.get("slug", "")

                    # Skip if already discovered
                    if slug in self.discovered_slugs:
                        continue

                    # Check if matches our pattern
                    if not re.match(MARKET_SLUGS_PATTERN, slug):
                        continue

                    # Build full context
                    try:
                        context = await self.market_fetcher.build_context(session, market)
                        self.discovered_slugs.add(slug)
                        new_markets.append(context)
                        print(f"[Discovery] New market: {slug}")
                    except Exception as e:
                        print(f"[Discovery] Error building context for {slug}: {e}")

        return new_markets

    async def _fetch_markets_for_asset(
        self,
        session: aiohttp.ClientSession,
        asset: str
    ) -> List[dict]:
        """Fetch markets for a specific asset (btc/eth)."""
        try:
            # Search for updown 15m markets
            async with session.get(
                f"{GAMMA_API}/markets",
                params={
                    "slug_contains": f"{asset}-updown-15m",
                    "closed": "false",  # Only open markets
                    "limit": 50
                },
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"[Discovery] Error fetching {asset} markets: {e}")
        return []

    async def discover_recent_resolved(self, hours_back: int = 24) -> List[MarketContext]:
        """
        Find recently resolved markets for backfill.
        Useful for catching up on markets that resolved while we were offline.
        """
        resolved_markets = []

        async with aiohttp.ClientSession() as session:
            for asset in ["btc", "eth"]:
                try:
                    async with session.get(
                        f"{GAMMA_API}/markets",
                        params={
                            "slug_contains": f"{asset}-updown-15m",
                            "closed": "true",
                            "limit": 100  # Get recent resolved
                        },
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as resp:
                        if resp.status != 200:
                            continue
                        markets = await resp.json()

                        for market in markets:
                            slug = market.get("slug", "")

                            # Skip if already discovered
                            if slug in self.discovered_slugs:
                                continue

                            # Check pattern
                            if not re.match(MARKET_SLUGS_PATTERN, slug):
                                continue

                            # Check if resolved within time window
                            end_date = parse_iso_datetime(market.get("endDate", ""))
                            if end_date:
                                now = datetime.now(timezone.utc)
                                if end_date.tzinfo is None:
                                    end_date = end_date.replace(tzinfo=timezone.utc)
                                hours_since = (now - end_date).total_seconds() / 3600

                                if hours_since <= hours_back:
                                    context = await self.market_fetcher.build_context(session, market)
                                    self.discovered_slugs.add(slug)
                                    resolved_markets.append(context)
                                    print(f"[Discovery] Recent resolved: {slug} ({hours_since:.1f}h ago)")

                except Exception as e:
                    print(f"[Discovery] Error fetching resolved {asset} markets: {e}")

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
