"""
Market discovery - finds 15-min BTC/ETH markets using timestamp-based slug generation.
"""

import aiohttp
import json
import time
from typing import List, Dict, Optional, Set
from datetime import datetime

from ..config import GAMMA_API, REQUEST_TIMEOUT
from ..database import Database
from ..logger import setup_logger

log = setup_logger(__name__)


class MarketDiscovery:
    """
    Discovers 15-minute markets using timestamp-based slug generation.

    15-min markets have predictable slugs: btc-updown-15m-{timestamp}
    where timestamp is rounded to 15-minute intervals.
    """

    def __init__(self, db: Database):
        self.db = db
        self.known_slugs: Set[str] = set()
        self._load_known_slugs()

    def _load_known_slugs(self):
        """Load known market slugs from database."""
        with self.db._get_conn() as conn:
            rows = conn.execute("SELECT slug FROM markets").fetchall()
            self.known_slugs = {row[0] for row in rows}
        log.info(f"Loaded {len(self.known_slugs)} known slugs")

    def _generate_potential_slugs(self) -> List[str]:
        """Generate potential slugs for current and upcoming 15-min markets."""
        now = int(time.time())

        # Round to 15-minute intervals
        interval = 15 * 60  # 15 minutes in seconds
        current_slot = (now // interval) * interval

        # Check current, next, and past slots (to catch recently resolved markets)
        slots = [
            current_slot - 3 * interval,  # -45 min (catch recently resolved)
            current_slot - 2 * interval,  # -30 min
            current_slot - interval,      # -15 min
            current_slot,                 # Current
            current_slot + interval,      # +15 min
            current_slot + 2 * interval,  # +30 min
        ]

        slugs = []
        for slot in slots:
            slugs.append(f"btc-updown-15m-{slot}")
            slugs.append(f"eth-updown-15m-{slot}")

        return slugs

    async def discover(self) -> List[Dict]:
        """
        Discover new markets by checking generated slugs against Gamma API.

        Returns list of newly discovered markets.
        """
        new_markets = []
        potential_slugs = self._generate_potential_slugs()

        async with aiohttp.ClientSession() as session:
            for slug in potential_slugs:
                if slug in self.known_slugs:
                    continue

                try:
                    market = await self._fetch_market_details(session, slug)
                    if market:
                        self.db.save_market(market)
                        self.known_slugs.add(slug)
                        new_markets.append(market)

                        end_str = ""
                        if market.get("end_time"):
                            end_dt = datetime.utcfromtimestamp(market["end_time"])
                            end_str = end_dt.strftime("%H:%M:%S")

                        log.info(f"New market discovered: {slug} (ends {end_str})")

                except Exception as e:
                    # Market doesn't exist - this is normal
                    pass

        return new_markets

    async def _fetch_market_details(
        self,
        session: aiohttp.ClientSession,
        slug: str
    ) -> Optional[Dict]:
        """Fetch market details from Gamma API."""
        url = f"{GAMMA_API}/markets"
        params = {"slug": slug}

        try:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                if not data:
                    return None

                # API returns list
                market_data = data[0] if isinstance(data, list) else data
                return self._parse_market(market_data)

        except Exception as e:
            return None

    def _parse_market(self, data: Dict) -> Dict:
        """Parse market data from Gamma API response."""
        # Parse token IDs from clobTokenIds
        clob_tokens = data.get("clobTokenIds", "[]")
        if isinstance(clob_tokens, str):
            try:
                clob_tokens = json.loads(clob_tokens)
            except:
                clob_tokens = []

        up_token = clob_tokens[0] if len(clob_tokens) > 0 else None
        down_token = clob_tokens[1] if len(clob_tokens) > 1 else None

        # Parse timestamps
        end_date_str = data.get("endDate")
        start_date_str = data.get("startDate")

        end_time = None
        if end_date_str:
            try:
                end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                end_time = int(end_dt.timestamp())
            except:
                pass

        start_time = None
        if start_date_str:
            try:
                start_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                start_time = int(start_dt.timestamp())
            except:
                pass

        # Check if resolved
        resolved = data.get("closed", False)
        winning_outcome = None
        if resolved:
            outcome_prices = data.get("outcomePrices", "[]")
            outcomes = data.get("outcomes", "[]")

            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except:
                    outcome_prices = []

            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except:
                    outcomes = []

            for i, price in enumerate(outcome_prices):
                if float(price) == 1.0 and i < len(outcomes):
                    winning_outcome = outcomes[i]
                    break

        return {
            "slug": data.get("slug", ""),
            "condition_id": data.get("conditionId", ""),
            "question": data.get("question", ""),
            "start_time": start_time,
            "end_time": end_time,
            "up_token_id": up_token,
            "down_token_id": down_token,
            "resolved": 1 if resolved else 0,
            "winning_outcome": winning_outcome,
            "trades_fetched": 0
        }
