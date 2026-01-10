"""
Fetch market metadata and ALL trades for a market.

Key difference from wallet-based fetching:
- Queries by token ID (makerAssetId/takerAssetId) instead of wallet
- Returns ALL trades in the market, not just one trader's trades
"""

import requests
import json
import time
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from .config import GAMMA_API, GOLDSKY_ENDPOINT, REQUEST_TIMEOUT, RATE_LIMIT_DELAY


def parse_iso_datetime(date_str: str) -> datetime:
    """
    Parse ISO datetime string robustly, handling various formats.
    Python 3.9's fromisoformat doesn't handle all ISO formats.
    """
    if not date_str:
        return datetime.now()

    # Remove 'Z' suffix and replace with +00:00
    date_str = date_str.replace("Z", "+00:00")

    # Try direct parsing first
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass

    # Handle varying microsecond precision (e.g., .67175 instead of .671750)
    # by truncating to 6 decimal places
    import re
    match = re.match(r'(.+\.)(\d+)(\+.+)', date_str)
    if match:
        prefix, micros, suffix = match.groups()
        # Pad or truncate to 6 digits
        micros = micros[:6].ljust(6, '0')
        date_str = f"{prefix}{micros}{suffix}"
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass

    # Fallback: strip fractional seconds entirely
    import re
    date_str = re.sub(r'\.\d+', '', date_str)
    return datetime.fromisoformat(date_str)


@dataclass
class MarketMetadata:
    """Metadata for a Polymarket market."""
    slug: str
    question: str
    condition_id: str
    token_ids: Dict[str, str]  # outcome -> token_id (e.g., {"up": "123...", "down": "456..."})
    outcomes: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    resolved: bool = False
    winning_outcome: Optional[str] = None
    outcome_prices: Optional[List[float]] = None


@dataclass
class RawTrade:
    """Raw trade data from Goldsky."""
    id: str
    tx_hash: str
    timestamp: int
    maker: str
    taker: str
    maker_asset_id: str
    taker_asset_id: str
    maker_amount: float  # Already divided by 1e6
    taker_amount: float  # Already divided by 1e6
    fee: float


@dataclass
class ParsedTrade:
    """Parsed trade with computed fields."""
    id: str
    tx_hash: str
    timestamp: int
    wallet: str
    role: str  # "maker" or "taker"
    side: str  # "BUY" or "SELL"
    outcome: str  # "Up" or "Down"
    shares: float
    usdc: float
    price: float
    fee: float


def parse_market_url(url: str) -> str:
    """
    Extract slug from Polymarket URL.

    Examples:
        https://polymarket.com/event/btc-updown-15m-1768037400/btc-updown-15m-1768037400
        -> btc-updown-15m-1768037400
    """
    # Pattern: /event/{slug}/{slug} or /event/{slug}
    match = re.search(r'/event/([^/]+)', url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not parse slug from URL: {url}")


def fetch_market_metadata(slug: str) -> Optional[MarketMetadata]:
    """
    Fetch market metadata from Gamma API by slug.

    Returns token IDs, outcomes, resolution status, etc.
    """
    try:
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"slug": slug},
            timeout=REQUEST_TIMEOUT
        )

        if resp.status_code != 200:
            print(f"  Error fetching metadata for {slug}: {resp.status_code}")
            return None

        markets = resp.json()
        if not markets:
            print(f"  No market found for slug: {slug}")
            return None

        market = markets[0] if isinstance(markets, list) else markets

        # Parse clobTokenIds and outcomes (they're JSON strings)
        clob_tokens = market.get("clobTokenIds", "[]")
        outcomes = market.get("outcomes", "[]")
        outcome_prices = market.get("outcomePrices")

        if isinstance(clob_tokens, str):
            clob_tokens = json.loads(clob_tokens)
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if isinstance(outcome_prices, str):
            outcome_prices = json.loads(outcome_prices)

        # Map outcomes to token IDs
        token_ids = {}
        for i, outcome in enumerate(outcomes):
            if i < len(clob_tokens):
                key = outcome.lower()
                token_ids[key] = clob_tokens[i]

        # Determine winning outcome from prices
        winning_outcome = None
        if outcome_prices and market.get("closed"):
            for i, price in enumerate(outcome_prices):
                if float(price) == 1.0 and i < len(outcomes):
                    winning_outcome = outcomes[i].lower()
                    break

        return MarketMetadata(
            slug=market.get("slug", slug),
            question=market.get("question", ""),
            condition_id=market.get("conditionId", ""),
            token_ids=token_ids,
            outcomes=outcomes,
            start_date=market.get("startDate"),
            end_date=market.get("endDate"),
            resolved=market.get("closed", False),
            winning_outcome=winning_outcome,
            outcome_prices=[float(p) for p in outcome_prices] if outcome_prices else None
        )

    except Exception as e:
        print(f"  Error fetching metadata for {slug}: {e}")
        return None


def _fetch_trades_by_field(
    field: str,
    token_id: str,
    start_ts: int,
    end_ts: int
) -> List[dict]:
    """
    Fetch trades where token_id matches either makerAssetId or takerAssetId.
    Uses cursor-based pagination (id_gt) to bypass 1000 limit.
    """
    all_trades = []
    last_id = ""
    batch_num = 0

    while True:
        batch_num += 1

        # Build where clause
        where = f'{field}: "{token_id}", timestamp_gte: "{start_ts}", timestamp_lt: "{end_ts}"'
        if last_id:
            where += f', id_gt: "{last_id}"'

        query = f'''{{
            orderFilledEvents(
                first: 1000,
                where: {{ {where} }},
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
        }}'''

        try:
            resp = requests.post(
                GOLDSKY_ENDPOINT,
                json={"query": query},
                timeout=REQUEST_TIMEOUT
            )
            data = resp.json()

            if "errors" in data:
                print(f"    Goldsky error: {data['errors']}")
                break

            events = data.get("data", {}).get("orderFilledEvents", [])
            if not events:
                break

            all_trades.extend(events)
            last_id = events[-1]["id"]

            if len(events) < 1000:
                break

            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            print(f"    Error fetching trades: {e}")
            break

    return all_trades


def fetch_all_market_trades(
    token_id: str,
    start_ts: int,
    end_ts: int
) -> List[dict]:
    """
    Fetch ALL trades involving a token (not filtered by wallet).

    Queries both:
    1. makerAssetId = token_id (maker selling this token)
    2. takerAssetId = token_id (maker buying this token)

    Returns deduplicated list of raw trade events.
    """
    all_trades = []
    seen_ids = set()

    # Query 1: Token as makerAssetId (maker selling)
    trades = _fetch_trades_by_field("makerAssetId", token_id, start_ts, end_ts)
    for t in trades:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            all_trades.append(t)

    time.sleep(RATE_LIMIT_DELAY)

    # Query 2: Token as takerAssetId (maker buying)
    trades = _fetch_trades_by_field("takerAssetId", token_id, start_ts, end_ts)
    for t in trades:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            all_trades.append(t)

    return all_trades


def parse_raw_trade(trade: dict, token_id: str, outcome: str) -> List[ParsedTrade]:
    """
    Convert raw Goldsky trade to parsed format.

    Returns TWO trades: one for maker, one for taker.

    Logic:
    - If makerAssetId == "0": Maker paid USDC, received shares = BUY for maker
    - If makerAssetId != "0": Maker paid shares, received USDC = SELL for maker
    - Taker always does the opposite of maker
    """
    ts = int(trade["timestamp"])

    if trade["makerAssetId"] == "0":
        # Maker bought shares (paid USDC)
        usdc = int(trade["makerAmountFilled"]) / 1e6
        shares = int(trade["takerAmountFilled"]) / 1e6
        maker_side = "BUY"
        taker_side = "SELL"
    else:
        # Maker sold shares (received USDC)
        shares = int(trade["makerAmountFilled"]) / 1e6
        usdc = int(trade["takerAmountFilled"]) / 1e6
        maker_side = "SELL"
        taker_side = "BUY"

    price = usdc / shares if shares > 0 else 0
    fee = int(trade["fee"]) / 1e6

    return [
        ParsedTrade(
            id=trade["id"],
            tx_hash=trade["transactionHash"],
            timestamp=ts,
            wallet=trade["maker"].lower(),
            role="maker",
            side=maker_side,
            outcome=outcome,
            shares=shares,
            usdc=usdc,
            price=price,
            fee=fee
        ),
        ParsedTrade(
            id=trade["id"],
            tx_hash=trade["transactionHash"],
            timestamp=ts,
            wallet=trade["taker"].lower(),
            role="taker",
            side=taker_side,
            outcome=outcome,
            shares=shares,
            usdc=usdc,
            price=price,
            fee=0  # Fee typically on taker, but we attribute to maker record
        )
    ]


def fetch_and_parse_market_trades(market: MarketMetadata) -> List[ParsedTrade]:
    """
    Fetch and parse all trades for a market.

    Returns list of ParsedTrade objects for all traders.
    """
    all_trades = []

    # Determine time range
    if market.start_date:
        start_dt = parse_iso_datetime(market.start_date)
        start_ts = int(start_dt.timestamp()) - 3600  # 1 hour buffer before
    else:
        start_ts = int(datetime.now().timestamp()) - 86400

    if market.end_date:
        end_dt = parse_iso_datetime(market.end_date)
        end_ts = int(end_dt.timestamp()) + 3600  # 1 hour buffer after
    else:
        end_ts = int(datetime.now().timestamp())

    # Fetch trades for each outcome token
    for outcome, token_id in market.token_ids.items():
        raw_trades = fetch_all_market_trades(token_id, start_ts, end_ts)

        for raw in raw_trades:
            # Determine which outcome this trade is for
            if raw["makerAssetId"] == token_id or raw["takerAssetId"] == token_id:
                parsed = parse_raw_trade(raw, token_id, outcome.capitalize())
                all_trades.extend(parsed)

        time.sleep(RATE_LIMIT_DELAY)

    return all_trades
