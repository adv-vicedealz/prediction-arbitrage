"""
Market context fetcher - gets orderbook and metadata for active markets.
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, Optional, List
from datetime import datetime, timezone

from .config import GAMMA_API, CLOB_API, REQUEST_TIMEOUT, MARKET_POLL_INTERVAL
from .models import MarketContext


def parse_iso_datetime(date_str: str) -> Optional[datetime]:
    """Parse ISO datetime string robustly."""
    if not date_str:
        return None

    # Remove 'Z' suffix and replace with +00:00
    date_str = date_str.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass

    # Handle varying microsecond precision
    match = re.match(r'(.+\.)(\d+)(\+.+)', date_str)
    if match:
        prefix, micros, suffix = match.groups()
        micros = micros[:6].ljust(6, '0')
        date_str = f"{prefix}{micros}{suffix}"
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass

    # Fallback: strip fractional seconds
    date_str = re.sub(r'\.\d+', '', date_str)
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None


class MarketContextFetcher:
    """Fetches and caches market metadata and orderbook data."""

    def __init__(self):
        self.cache: Dict[str, MarketContext] = {}
        self.running = False

    async def fetch_market_by_slug(
        self,
        session: aiohttp.ClientSession,
        slug: str
    ) -> Optional[dict]:
        """Fetch market metadata from Gamma API by slug."""
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
            print(f"Error fetching market {slug}: {e}")
        return None

    async def fetch_market_by_token(
        self,
        session: aiohttp.ClientSession,
        token_id: str
    ) -> Optional[dict]:
        """Fetch market metadata from Gamma API by token ID."""
        try:
            async with session.get(
                f"{GAMMA_API}/markets",
                params={"clob_token_ids": token_id},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    markets = await resp.json()
                    if markets:
                        return markets[0] if isinstance(markets, list) else markets
        except Exception as e:
            print(f"Error fetching market for token {token_id[:20]}...: {e}")
        return None

    async def fetch_orderbook(
        self,
        session: aiohttp.ClientSession,
        token_id: str
    ) -> dict:
        """Fetch live orderbook from CLOB API."""
        try:
            async with session.get(
                f"{CLOB_API}/book",
                params={"token_id": token_id},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error fetching orderbook for {token_id[:20]}...: {e}")
        return {"bids": [], "asks": []}

    async def build_context(
        self,
        session: aiohttp.ClientSession,
        market: dict
    ) -> MarketContext:
        """Build full market context with orderbook data."""
        # Parse token IDs and outcomes
        clob_tokens = market.get("clobTokenIds", "[]")
        outcomes = market.get("outcomes", "[]")

        if isinstance(clob_tokens, str):
            clob_tokens = json.loads(clob_tokens)
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)

        # Map outcomes to tokens (lowercase keys)
        token_ids = {}
        for i, outcome in enumerate(outcomes):
            if i < len(clob_tokens):
                token_ids[outcome.lower()] = clob_tokens[i]

        # Determine up/down tokens
        up_token = token_ids.get("up", clob_tokens[0] if clob_tokens else "")
        down_token = token_ids.get("down", clob_tokens[1] if len(clob_tokens) > 1 else "")

        # Fetch orderbooks concurrently
        up_book, down_book = await asyncio.gather(
            self.fetch_orderbook(session, up_token) if up_token else asyncio.sleep(0, {}),
            self.fetch_orderbook(session, down_token) if down_token else asyncio.sleep(0, {})
        )

        # Parse best prices
        # CLOB API returns bids sorted ascending, so best bid is last
        up_bids = up_book.get("bids", []) if isinstance(up_book, dict) else []
        up_asks = up_book.get("asks", []) if isinstance(up_book, dict) else []
        down_bids = down_book.get("bids", []) if isinstance(down_book, dict) else []
        down_asks = down_book.get("asks", []) if isinstance(down_book, dict) else []

        up_best_bid = max((float(b["price"]) for b in up_bids), default=None)
        up_best_ask = min((float(a["price"]) for a in up_asks), default=None)
        down_best_bid = max((float(b["price"]) for b in down_bids), default=None)
        down_best_ask = min((float(a["price"]) for a in down_asks), default=None)

        combined_bid = None
        spread = None
        if up_best_bid is not None and down_best_bid is not None:
            combined_bid = up_best_bid + down_best_bid
            spread = 1.0 - combined_bid

        # Parse dates
        start_date = parse_iso_datetime(market.get("startDate", ""))
        end_date = parse_iso_datetime(market.get("endDate", ""))

        time_to_resolution = 0
        if end_date:
            now = datetime.now(timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            time_to_resolution = max(0, (end_date - now).total_seconds() / 60)

        # Determine winning outcome
        winning_outcome = None
        outcome_prices = market.get("outcomePrices")
        if outcome_prices and market.get("closed"):
            if isinstance(outcome_prices, str):
                outcome_prices = json.loads(outcome_prices)
            for i, price in enumerate(outcome_prices):
                if float(price) == 1.0 and i < len(outcomes):
                    winning_outcome = outcomes[i].lower()
                    break

        return MarketContext(
            slug=market.get("slug", ""),
            question=market.get("question", ""),
            condition_id=market.get("conditionId", ""),
            token_ids=token_ids,
            outcomes=outcomes,
            start_date=start_date,
            end_date=end_date,
            time_to_resolution_mins=time_to_resolution,
            resolved=market.get("closed", False),
            winning_outcome=winning_outcome,
            up_best_bid=up_best_bid,
            up_best_ask=up_best_ask,
            down_best_bid=down_best_bid,
            down_best_ask=down_best_ask,
            combined_bid=combined_bid,
            spread=spread
        )

    async def get_or_fetch_context(
        self,
        slug: str = None,
        token_id: str = None
    ) -> Optional[MarketContext]:
        """Get market context from cache or fetch it."""
        # Check cache first
        if slug and slug in self.cache:
            return self.cache[slug]

        async with aiohttp.ClientSession() as session:
            market = None

            if slug:
                market = await self.fetch_market_by_slug(session, slug)
            elif token_id:
                market = await self.fetch_market_by_token(session, token_id)

            if market:
                context = await self.build_context(session, market)
                self.cache[context.slug] = context
                return context

        return None

    async def refresh_context(self, slug: str) -> Optional[MarketContext]:
        """Refresh orderbook data for a cached market."""
        if slug not in self.cache:
            return await self.get_or_fetch_context(slug=slug)

        async with aiohttp.ClientSession() as session:
            market = await self.fetch_market_by_slug(session, slug)
            if market:
                context = await self.build_context(session, market)
                self.cache[slug] = context
                return context

        return None

    async def refresh_all(self) -> List[MarketContext]:
        """Refresh all cached markets."""
        refreshed = []
        for slug in list(self.cache.keys()):
            context = await self.refresh_context(slug)
            if context:
                refreshed.append(context)
        return refreshed

    async def run(self):
        """Periodically refresh orderbook data for active markets."""
        self.running = True
        print(f"Market context fetcher started...")

        while self.running:
            try:
                if self.cache:
                    await self.refresh_all()
                    print(f"Refreshed {len(self.cache)} market contexts")
            except Exception as e:
                print(f"Market refresh error: {e}")

            await asyncio.sleep(MARKET_POLL_INTERVAL)

    def stop(self):
        """Stop the refresh loop."""
        self.running = False

    def get_active_markets(self) -> List[MarketContext]:
        """Get all active (non-resolved) markets."""
        return [m for m in self.cache.values() if not m.resolved]

    def cleanup_old_markets(self, hours_back: int = 2) -> tuple:
        """Remove old resolved markets from cache to prevent memory bloat.

        Returns tuple of (removed_slugs, removed_token_ids).
        """
        now = datetime.now(timezone.utc)
        cutoff_seconds = hours_back * 3600
        removed_slugs = []
        removed_token_ids = []

        for slug in list(self.cache.keys()):
            ctx = self.cache.get(slug)
            if ctx and ctx.resolved and ctx.end_date:
                # Make sure end_date is timezone-aware
                end_date = ctx.end_date
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                age_seconds = (now - end_date).total_seconds()
                if age_seconds > cutoff_seconds:
                    # Collect token IDs before removing
                    for token_id in ctx.token_ids.values():
                        if token_id:
                            removed_token_ids.append(token_id)
                    del self.cache[slug]
                    removed_slugs.append(slug)

        if removed_slugs:
            print(f"[MarketContext] Cleaned up {len(removed_slugs)} old markets from cache")

        return removed_slugs, removed_token_ids
