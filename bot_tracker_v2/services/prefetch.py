"""
Startup prefetch - loads historical data for the last N markets on boot.
Ensures dashboard has data immediately after deployment.
"""

import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Set

from ..config import GAMMA_API, TARGET_WALLETS, REQUEST_TIMEOUT
from ..database import Database
from ..logger import setup_logger
from .fetcher import TradeFetcher, GOLDSKY_SUBGRAPH

log = setup_logger(__name__)

# Number of historical markets to prefetch
PREFETCH_MARKET_COUNT = 10


class StartupPrefetch:
    """
    Prefetches historical market data on startup.

    1. Queries Goldsky to find recent markets the user traded
    2. Fetches market details from Gamma API
    3. Fetches all trades via existing TradeFetcher
    """

    def __init__(self, db: Database, fetcher: TradeFetcher):
        self.db = db
        self.fetcher = fetcher

    async def run(self, count: int = PREFETCH_MARKET_COUNT):
        """
        Prefetch the last N markets on startup.

        Args:
            count: Number of markets to prefetch
        """
        log.info(f"Starting prefetch of last {count} markets...")

        # Get already-fetched markets
        existing_markets = self._get_existing_markets()
        log.info(f"Found {len(existing_markets)} markets already in DB")

        # Find recent markets from user trades
        recent_markets = await self._discover_recent_markets(count * 2)  # Get extra to account for duplicates

        if not recent_markets:
            log.warning("No recent markets found to prefetch")
            return

        log.info(f"Discovered {len(recent_markets)} recent markets from trades")

        # Filter out already-fetched markets
        markets_to_fetch = []
        for market in recent_markets:
            if market["slug"] not in existing_markets:
                markets_to_fetch.append(market)
                if len(markets_to_fetch) >= count:
                    break

        if not markets_to_fetch:
            log.info("All recent markets already fetched")
            return

        log.info(f"Prefetching {len(markets_to_fetch)} markets...")

        # Fetch trades for each market
        total_trades = 0
        for i, market in enumerate(markets_to_fetch, 1):
            try:
                log.info(f"[{i}/{len(markets_to_fetch)}] Fetching {market['slug']}...")

                # Save market to DB first
                self.db.save_market(market)

                # Fetch trades
                trades = await self.fetcher.fetch_market_trades(market)
                total_trades += len(trades)

                log.info(f"[{i}/{len(markets_to_fetch)}] Fetched {len(trades)} trades for {market['slug']}")

            except Exception as e:
                log.error(f"Error prefetching {market['slug']}: {e}")

        log.info(f"Prefetch complete: {total_trades} trades from {len(markets_to_fetch)} markets")

    def _get_existing_markets(self) -> Set[str]:
        """Get set of market slugs already in database."""
        try:
            with self.db._get_conn() as conn:
                rows = conn.execute(
                    "SELECT slug FROM markets WHERE trades_fetched = 1"
                ).fetchall()
                return {row["slug"] for row in rows}
        except Exception:
            return set()

    async def _discover_recent_markets(self, limit: int) -> List[Dict]:
        """
        Discover recent markets by querying user's trades on Goldsky.

        Returns list of market dicts with slug, token IDs, etc.
        """
        markets = {}

        async with aiohttp.ClientSession() as session:
            # Query trades for each wallet
            for wallet_address in TARGET_WALLETS.keys():
                wallet = wallet_address.lower()

                # Get recent trades as maker and taker
                for role in ["maker", "taker"]:
                    slugs = await self._get_recent_trade_slugs(session, wallet, role, limit)

                    # Fetch market details for each unique slug
                    for slug in slugs:
                        if slug not in markets:
                            market_info = await self._fetch_market_info(session, slug)
                            if market_info:
                                markets[slug] = market_info

        # Sort by end_time descending (most recent first)
        sorted_markets = sorted(
            markets.values(),
            key=lambda m: m.get("end_time", 0) or 0,
            reverse=True
        )

        return sorted_markets[:limit]

    async def _get_recent_trade_slugs(
        self,
        session: aiohttp.ClientSession,
        wallet: str,
        role: str,
        limit: int
    ) -> List[str]:
        """Get unique market slugs from recent trades."""
        slugs = []
        seen_tokens = set()

        # Query recent orderFilledEvents
        query = f"""{{
            orderFilledEvents(
                first: {limit * 10},
                where: {{ {role}: "{wallet}" }},
                orderBy: timestamp,
                orderDirection: desc
            ) {{
                makerAssetId
                takerAssetId
                timestamp
            }}
        }}"""

        try:
            async with session.post(
                GOLDSKY_SUBGRAPH,
                json={"query": query},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()
                events = data.get("data", {}).get("orderFilledEvents", [])

                for event in events:
                    # Extract non-USDC token (the outcome token)
                    maker_asset = event.get("makerAssetId", "0")
                    taker_asset = event.get("takerAssetId", "0")

                    # USDC is typically "0" in the CLOB
                    token = maker_asset if maker_asset != "0" else taker_asset

                    if token and token != "0" and token not in seen_tokens:
                        seen_tokens.add(token)

                        # Look up market slug from token
                        slug = await self._get_slug_from_token(session, token)
                        if slug and slug not in slugs:
                            slugs.append(slug)

                            if len(slugs) >= limit:
                                return slugs

        except Exception as e:
            log.error(f"Error querying recent trades: {e}")

        return slugs

    async def _get_slug_from_token(
        self,
        session: aiohttp.ClientSession,
        token_id: str
    ) -> str:
        """Look up market slug from token ID via Gamma API."""
        try:
            async with session.get(
                f"{GAMMA_API}/markets",
                params={"clob_token_ids": token_id},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                if data and len(data) > 0:
                    # Extract slug from market data
                    market = data[0]

                    # Get slug from event or generate from question
                    slug = market.get("slug")
                    if not slug:
                        # Try to get from groupItemTitle
                        slug = market.get("groupItemTitle", "").lower().replace(" ", "-")

                    return slug

        except Exception as e:
            log.debug(f"Error looking up token {token_id}: {e}")

        return None

    async def _fetch_market_info(
        self,
        session: aiohttp.ClientSession,
        slug: str
    ) -> Dict:
        """Fetch market details from Gamma API."""
        try:
            # Try events endpoint first
            async with session.get(
                f"{GAMMA_API}/events",
                params={"slug": slug},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        event = data[0] if isinstance(data, list) else data
                        markets = event.get("markets", [])

                        if markets:
                            market = markets[0]
                            return self._parse_market_data(market, slug)

            # Fallback to markets endpoint
            async with session.get(
                f"{GAMMA_API}/markets",
                params={"slug": slug},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        market = data[0] if isinstance(data, list) else data
                        return self._parse_market_data(market, slug)

        except Exception as e:
            log.error(f"Error fetching market info for {slug}: {e}")

        return None

    def _parse_market_data(self, market: Dict, slug: str) -> Dict:
        """Parse Gamma API market data into our format."""
        try:
            # Parse token IDs
            tokens = market.get("clobTokenIds", "[]")
            if isinstance(tokens, str):
                tokens = json.loads(tokens)

            up_token = tokens[0] if len(tokens) > 0 else None
            down_token = tokens[1] if len(tokens) > 1 else None

            # Parse end time
            end_date = market.get("endDate")
            end_time = None
            if end_date:
                if isinstance(end_date, int):
                    end_time = end_date if end_date < 2000000000 else end_date // 1000
                elif isinstance(end_date, str):
                    try:
                        dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        end_time = int(dt.timestamp())
                    except:
                        pass

            # Calculate start time (15 min before end for 15-min markets)
            start_time = end_time - 900 if end_time else None

            return {
                "slug": slug,
                "condition_id": market.get("conditionId"),
                "question": market.get("question", ""),
                "start_time": start_time,
                "end_time": end_time,
                "up_token_id": up_token,
                "down_token_id": down_token
            }

        except Exception as e:
            log.error(f"Error parsing market data: {e}")
            return None
