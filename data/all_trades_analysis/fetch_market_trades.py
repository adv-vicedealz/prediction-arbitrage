#!/usr/bin/env python3
"""
Fetch all trades for a Polymarket market.

Usage:
    python fetch_market_trades.py [market_url_or_slug]

If no argument provided, uses the default market URL.

Output:
    Saves trades to trades_{timestamp}.json in the same directory.
"""

import requests
import json
import time
import re
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


# API Endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
GOLDSKY_ENDPOINT = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"

# Request settings
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 0.2

# Default market URL
DEFAULT_MARKET_URL = "https://polymarket.com/event/btc-updown-15m-1768044600/btc-updown-15m-1768044600"


@dataclass
class MarketMetadata:
    """Metadata for a Polymarket market."""
    slug: str
    question: str
    condition_id: str
    token_ids: Dict[str, str]
    outcomes: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    resolved: bool = False
    winning_outcome: Optional[str] = None


@dataclass
class ParsedTrade:
    """Parsed trade with computed fields."""
    id: str
    tx_hash: str
    timestamp: int
    timestamp_readable: str
    wallet: str
    role: str
    side: str
    outcome: str
    shares: float
    usdc: float
    price: float
    fee: float


def parse_market_url(url: str) -> str:
    """Extract slug from Polymarket URL."""
    match = re.search(r'/event/([^/]+)', url)
    if match:
        return match.group(1)
    # If not a URL, assume it's already a slug
    return url


def parse_iso_datetime(date_str: str) -> datetime:
    """Parse ISO datetime string robustly."""
    if not date_str:
        return datetime.now()

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
    return datetime.fromisoformat(date_str)


def fetch_market_metadata(slug: str) -> Optional[MarketMetadata]:
    """Fetch market metadata from Gamma API by slug."""
    print(f"Fetching metadata for: {slug}")

    try:
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"slug": slug},
            timeout=REQUEST_TIMEOUT
        )

        if resp.status_code != 200:
            print(f"  Error: HTTP {resp.status_code}")
            return None

        markets = resp.json()
        if not markets:
            print(f"  No market found for slug: {slug}")
            return None

        market = markets[0] if isinstance(markets, list) else markets

        # Parse JSON fields
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
                token_ids[outcome.lower()] = clob_tokens[i]

        # Determine winning outcome
        winning_outcome = None
        if outcome_prices and market.get("closed"):
            for i, price in enumerate(outcome_prices):
                if float(price) == 1.0 and i < len(outcomes):
                    winning_outcome = outcomes[i].lower()
                    break

        metadata = MarketMetadata(
            slug=market.get("slug", slug),
            question=market.get("question", ""),
            condition_id=market.get("conditionId", ""),
            token_ids=token_ids,
            outcomes=outcomes,
            start_date=market.get("startDate"),
            end_date=market.get("endDate"),
            resolved=market.get("closed", False),
            winning_outcome=winning_outcome
        )

        print(f"  Question: {metadata.question}")
        print(f"  Condition ID: {metadata.condition_id[:20]}...")
        print(f"  Token IDs: {list(metadata.token_ids.keys())}")
        print(f"  Resolved: {metadata.resolved}")
        if metadata.winning_outcome:
            print(f"  Winner: {metadata.winning_outcome}")

        return metadata

    except Exception as e:
        print(f"  Error: {e}")
        return None


def fetch_trades_by_field(
    field: str,
    token_id: str,
    start_ts: int,
    end_ts: int
) -> List[dict]:
    """Fetch trades with cursor-based pagination."""
    all_trades = []
    last_id = ""
    batch_num = 0

    while True:
        batch_num += 1

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

            if batch_num % 5 == 0:
                print(f"    Fetched {len(all_trades)} trades so far...")

            if len(events) < 1000:
                break

            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            print(f"    Error: {e}")
            break

    return all_trades


def fetch_all_market_trades(token_id: str, start_ts: int, end_ts: int) -> List[dict]:
    """Fetch ALL trades for a token (both buy and sell sides)."""
    all_trades = []
    seen_ids = set()

    # Query 1: Token as makerAssetId (maker selling)
    print(f"    Fetching sells...")
    trades = fetch_trades_by_field("makerAssetId", token_id, start_ts, end_ts)
    for t in trades:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            all_trades.append(t)

    time.sleep(RATE_LIMIT_DELAY)

    # Query 2: Token as takerAssetId (maker buying)
    print(f"    Fetching buys...")
    trades = fetch_trades_by_field("takerAssetId", token_id, start_ts, end_ts)
    for t in trades:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            all_trades.append(t)

    return all_trades


def parse_raw_trade(trade: dict, outcome: str) -> List[ParsedTrade]:
    """Convert raw trade to parsed format (returns maker + taker trades)."""
    ts = int(trade["timestamp"])
    ts_readable = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")

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
            timestamp_readable=ts_readable,
            wallet=trade["maker"].lower(),
            role="maker",
            side=maker_side,
            outcome=outcome,
            shares=round(shares, 6),
            usdc=round(usdc, 6),
            price=round(price, 6),
            fee=round(fee, 6)
        ),
        ParsedTrade(
            id=trade["id"],
            tx_hash=trade["transactionHash"],
            timestamp=ts,
            timestamp_readable=ts_readable,
            wallet=trade["taker"].lower(),
            role="taker",
            side=taker_side,
            outcome=outcome,
            shares=round(shares, 6),
            usdc=round(usdc, 6),
            price=round(price, 6),
            fee=0
        )
    ]


def fetch_and_parse_all_trades(market: MarketMetadata) -> List[ParsedTrade]:
    """Fetch and parse all trades for a market."""
    all_trades = []

    # Determine time range with buffer
    if market.start_date:
        start_dt = parse_iso_datetime(market.start_date)
        start_ts = int(start_dt.timestamp()) - 3600  # 1 hour before
    else:
        start_ts = int(datetime.now().timestamp()) - 86400

    if market.end_date:
        end_dt = parse_iso_datetime(market.end_date)
        end_ts = int(end_dt.timestamp()) + 3600  # 1 hour after
    else:
        end_ts = int(datetime.now().timestamp())

    print(f"\nTime range: {datetime.utcfromtimestamp(start_ts)} to {datetime.utcfromtimestamp(end_ts)}")

    # Fetch trades for each outcome token
    for outcome, token_id in market.token_ids.items():
        print(f"\nFetching {outcome.upper()} trades (token: {token_id[:20]}...)")

        raw_trades = fetch_all_market_trades(token_id, start_ts, end_ts)
        print(f"  Found {len(raw_trades)} raw trades")

        for raw in raw_trades:
            parsed = parse_raw_trade(raw, outcome.capitalize())
            all_trades.extend(parsed)

        time.sleep(RATE_LIMIT_DELAY)

    # Sort by timestamp
    all_trades.sort(key=lambda t: (t.timestamp, t.id))

    return all_trades


def main():
    """Main entry point."""
    # Get market URL from args or use default
    if len(sys.argv) > 1:
        market_input = sys.argv[1]
    else:
        market_input = DEFAULT_MARKET_URL

    print("=" * 60)
    print("POLYMARKET TRADE FETCHER")
    print("=" * 60)
    print(f"\nInput: {market_input}")

    # Extract slug
    slug = parse_market_url(market_input)
    print(f"Slug: {slug}")

    # Extract timestamp from slug for output filename
    match = re.search(r'(\d{10})$', slug)
    timestamp_suffix = match.group(1) if match else datetime.now().strftime("%Y%m%d_%H%M%S")

    # Fetch market metadata
    print("\n" + "-" * 40)
    print("STEP 1: Fetching Market Metadata")
    print("-" * 40)

    metadata = fetch_market_metadata(slug)
    if not metadata:
        print("Failed to fetch market metadata. Exiting.")
        sys.exit(1)

    # Fetch all trades
    print("\n" + "-" * 40)
    print("STEP 2: Fetching All Trades")
    print("-" * 40)

    trades = fetch_and_parse_all_trades(metadata)
    print(f"\nTotal parsed trades: {len(trades)}")

    # Calculate stats
    unique_wallets = len(set(t.wallet for t in trades))
    unique_events = len(set(t.id for t in trades))
    total_volume = sum(t.usdc for t in trades if t.role == "maker")  # Count once per event

    print(f"Unique trade events: {unique_events}")
    print(f"Unique wallets: {unique_wallets}")
    print(f"Total volume: ${total_volume:,.2f}")

    # Build output
    output = {
        "market": {
            "slug": metadata.slug,
            "question": metadata.question,
            "condition_id": metadata.condition_id,
            "token_ids": metadata.token_ids,
            "outcomes": metadata.outcomes,
            "start_date": metadata.start_date,
            "end_date": metadata.end_date,
            "resolved": metadata.resolved,
            "winning_outcome": metadata.winning_outcome
        },
        "fetch_info": {
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "total_trade_records": len(trades),
            "unique_events": unique_events,
            "unique_wallets": unique_wallets,
            "total_volume_usdc": round(total_volume, 2)
        },
        "trades": [asdict(t) for t in trades]
    }

    # Save to file
    output_dir = Path(__file__).parent
    output_file = output_dir / f"trades_{timestamp_suffix}.json"

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "-" * 40)
    print("COMPLETE")
    print("-" * 40)
    print(f"Output saved to: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
