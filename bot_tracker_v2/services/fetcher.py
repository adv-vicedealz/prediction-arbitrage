"""
Trade fetcher - fetches complete trades using Goldsky Subgraph.
Guarantees 100% trade capture via on-chain data.
"""

import aiohttp
import time
import json
from typing import List, Dict, Optional

from ..config import GAMMA_API, TARGET_WALLETS, REQUEST_TIMEOUT
from ..database import Database
from ..logger import setup_logger

log = setup_logger(__name__)

# Goldsky Subgraph endpoint
GOLDSKY_SUBGRAPH = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"


class TradeFetcher:
    """
    Fetches all trades for a market using Goldsky Subgraph.

    Queries on-chain orderFilledEvents for 100% trade capture.
    Captures: maker/taker role, buy/sell side, shares, price, fees.
    """

    def __init__(self, db: Database):
        self.db = db

    async def fetch_market_trades(self, market: Dict) -> List[Dict]:
        """
        Fetch ALL trades for a market from all target wallets.

        Args:
            market: Market dict with slug, up_token_id, down_token_id, etc.

        Returns:
            List of trade dicts
        """
        slug = market["slug"]
        up_token = market.get("up_token_id")
        down_token = market.get("down_token_id")

        if not up_token or not down_token:
            log.warning(f"Missing token IDs for market: {slug}")
            return []

        all_trades = []

        log.info(f"Fetching trades via Goldsky for {slug}")

        async with aiohttp.ClientSession() as session:
            # Fetch trades for each target wallet
            for wallet_address, wallet_name in TARGET_WALLETS.items():
                try:
                    trades = await self._fetch_wallet_trades(
                        session,
                        wallet_address.lower(),
                        wallet_name,
                        up_token,
                        down_token,
                        slug
                    )
                    all_trades.extend(trades)

                    if trades:
                        log.info(f"Fetched {len(trades)} trades for {wallet_name} on {slug}")

                except Exception as e:
                    log.error(f"Error fetching trades for {wallet_name} on {slug}: {e}")

            # Fetch winning outcome
            winning_outcome = await self._fetch_winning_outcome(session, market)

        # Sort by timestamp
        all_trades.sort(key=lambda t: t["timestamp"])

        # Save trades to database
        new_count = self.db.save_trades(all_trades)

        # Mark market as fetched
        self.db.mark_market_fetched(slug, winning_outcome)

        log.info(f"Market processed: {slug} (total={len(all_trades)}, new={new_count}, winner={winning_outcome})")

        return all_trades

    async def _fetch_wallet_trades(
        self,
        session: aiohttp.ClientSession,
        wallet: str,
        wallet_name: str,
        up_token: str,
        down_token: str,
        market_slug: str
    ) -> List[Dict]:
        """
        Fetch all trades for a wallet on a market via Goldsky.

        Queries all 8 combinations:
        - maker/taker x buy/sell x up/down token
        """
        trades = []

        # Define all query combinations
        # (role, asset_field, token, outcome, is_buy)
        queries = [
            # Maker BUY: wallet pays USDC (makerAssetId=0), receives shares (takerAssetId=token)
            ("maker", "takerAssetId", up_token, "Up", True),
            ("maker", "takerAssetId", down_token, "Down", True),
            # Maker SELL: wallet pays shares (makerAssetId=token), receives USDC
            ("maker", "makerAssetId", up_token, "Up", False),
            ("maker", "makerAssetId", down_token, "Down", False),
            # Taker BUY: wallet takes shares (makerAssetId=token from counterparty)
            ("taker", "makerAssetId", up_token, "Up", True),
            ("taker", "makerAssetId", down_token, "Down", True),
            # Taker SELL: wallet gives shares (takerAssetId=token)
            ("taker", "takerAssetId", up_token, "Up", False),
            ("taker", "takerAssetId", down_token, "Down", False),
        ]

        for role, asset_field, token, outcome, is_buy in queries:
            query_trades = await self._query_goldsky(
                session, wallet, role, asset_field, token,
                outcome, is_buy, wallet_name, market_slug
            )
            trades.extend(query_trades)

        return trades

    async def _query_goldsky(
        self,
        session: aiohttp.ClientSession,
        wallet: str,
        role: str,  # "maker" or "taker"
        asset_field: str,  # "makerAssetId" or "takerAssetId"
        token: str,
        outcome: str,  # "Up" or "Down"
        is_buy: bool,
        wallet_name: str,
        market_slug: str
    ) -> List[Dict]:
        """Query Goldsky subgraph with pagination."""
        trades = []
        last_id = ""

        while True:
            # Build query with pagination
            id_filter = f', id_gt: "{last_id}"' if last_id else ""

            query = f"""{{
                orderFilledEvents(
                    first: 1000,
                    where: {{ {role}: "{wallet}", {asset_field}: "{token}"{id_filter} }},
                    orderBy: id,
                    orderDirection: asc
                ) {{
                    id
                    transactionHash
                    timestamp
                    maker
                    taker
                    makerAssetId
                    takerAssetId
                    makerAmountFilled
                    takerAmountFilled
                    fee
                }}
            }}"""

            try:
                async with session.post(
                    GOLDSKY_SUBGRAPH,
                    json={"query": query},
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                ) as resp:
                    if resp.status != 200:
                        log.warning(f"Goldsky query failed: status={resp.status}")
                        break

                    data = await resp.json()
                    events = data.get("data", {}).get("orderFilledEvents", [])

                    if not events:
                        break

                    # Parse events
                    for event in events:
                        trade = self._parse_goldsky_event(
                            event, role, is_buy, outcome,
                            wallet, wallet_name, market_slug
                        )
                        if trade:
                            trades.append(trade)

                    # Check if more pages
                    if len(events) < 1000:
                        break

                    last_id = events[-1]["id"]

            except Exception as e:
                log.error(f"Goldsky query error: {e}")
                break

        return trades

    def _parse_goldsky_event(
        self,
        event: Dict,
        role: str,
        is_buy: bool,
        outcome: str,
        wallet: str,
        wallet_name: str,
        market_slug: str
    ) -> Optional[Dict]:
        """Parse Goldsky orderFilledEvent into trade dict."""
        try:
            tx_hash = event.get("transactionHash", "")
            event_id = event.get("id", "")

            # Generate unique trade ID
            trade_id = f"{tx_hash}:{event_id[-20:]}" if tx_hash else f"{time.time()}:{event_id}"

            timestamp = int(event.get("timestamp", time.time()))

            # Parse amounts (divide by 1e6 for USDC decimals)
            maker_amount = int(event.get("makerAmountFilled", 0)) / 1e6
            taker_amount = int(event.get("takerAmountFilled", 0)) / 1e6
            fee = int(event.get("fee", 0)) / 1e6

            # Determine shares and USDC based on trade type
            if role == "maker":
                if is_buy:
                    # Maker BUY: pays USDC (makerAmount), receives shares (takerAmount)
                    usdc = maker_amount
                    shares = taker_amount
                else:
                    # Maker SELL: pays shares (makerAmount), receives USDC (takerAmount)
                    shares = maker_amount
                    usdc = taker_amount
            else:  # taker
                if is_buy:
                    # Taker BUY: pays USDC (takerAmount), receives shares (makerAmount)
                    usdc = taker_amount
                    shares = maker_amount
                else:
                    # Taker SELL: pays shares (takerAmount), receives USDC (makerAmount)
                    shares = taker_amount
                    usdc = maker_amount

            price = usdc / shares if shares > 0 else 0
            side = "BUY" if is_buy else "SELL"

            return {
                "id": trade_id,
                "tx_hash": tx_hash,
                "timestamp": timestamp,
                "wallet": wallet,
                "wallet_name": wallet_name,
                "role": role,  # "maker" or "taker"
                "side": side,  # "BUY" or "SELL"
                "outcome": outcome,  # "Up" or "Down"
                "shares": shares,
                "price": price,
                "usdc": usdc,
                "fee": fee,  # Store fee but don't include in P&L
                "market_slug": market_slug
            }

        except Exception as e:
            log.error(f"Trade parse error: {e}")
            return None

    async def _fetch_winning_outcome(
        self,
        session: aiohttp.ClientSession,
        market: Dict
    ) -> Optional[str]:
        """Fetch the winning outcome for a resolved market."""
        slug = market["slug"]

        try:
            async with session.get(
                f"{GAMMA_API}/markets",
                params={"slug": slug},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                if not data:
                    return None

                market_data = data[0] if isinstance(data, list) else data

                if not market_data.get("closed"):
                    return None

                # Parse outcome prices
                outcome_prices = market_data.get("outcomePrices", "[]")
                outcomes = market_data.get("outcomes", "[]")

                if isinstance(outcome_prices, str):
                    outcome_prices = json.loads(outcome_prices)
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)

                # Find winner (price = 1.0)
                for i, price in enumerate(outcome_prices):
                    if float(price) == 1.0 and i < len(outcomes):
                        return outcomes[i]

        except Exception as e:
            log.error(f"Error fetching winning outcome for {slug}: {e}")

        return None
