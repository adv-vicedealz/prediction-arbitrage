"""Debug SELL trades - compare Goldsky vs Polymarket API"""

import requests
from datetime import datetime

GOLDSKY = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"
TARGET_WALLET = "0x0ea574f3204c5c9c0cdead90392ea0990f4d17e4"

# Token IDs for btc-updown-15m-1768050900
UP_TOKEN = "297478145107466476230486066113275432075504678169319680317187259974298847416"
DOWN_TOKEN = "66872178996997529167823776739284034977906453018324771475745386189093976672398"

START_TS = 1768050000
END_TS = 1768052000


def fetch_goldsky_maker_events():
    """Fetch events where our wallet is the MAKER."""
    query = f'''{{
        orderFilledEvents(
            first: 500,
            where: {{
                maker: "{TARGET_WALLET.lower()}",
                timestamp_gte: "{START_TS}",
                timestamp_lt: "{END_TS}"
            }},
            orderBy: timestamp,
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
        }}
    }}'''

    resp = requests.post(GOLDSKY, json={"query": query}, timeout=30)
    data = resp.json()
    return data.get("data", {}).get("orderFilledEvents", [])


def fetch_goldsky_taker_events():
    """Fetch events where our wallet is the TAKER."""
    query = f'''{{
        orderFilledEvents(
            first: 500,
            where: {{
                taker: "{TARGET_WALLET.lower()}",
                timestamp_gte: "{START_TS}",
                timestamp_lt: "{END_TS}"
            }},
            orderBy: timestamp,
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
        }}
    }}'''

    resp = requests.post(GOLDSKY, json={"query": query}, timeout=30)
    data = resp.json()
    return data.get("data", {}).get("orderFilledEvents", [])


def parse_event(e, wallet):
    """Parse an event to determine BUY/SELL from wallet's perspective."""
    is_maker = e["maker"].lower() == wallet.lower()

    # Determine outcome token
    if e["makerAssetId"] in [UP_TOKEN, DOWN_TOKEN]:
        token_id = e["makerAssetId"]
    elif e["takerAssetId"] in [UP_TOKEN, DOWN_TOKEN]:
        token_id = e["takerAssetId"]
    else:
        return None  # Not a trade for this market

    outcome = "Up" if token_id == UP_TOKEN else "Down"

    if e["makerAssetId"] == "0":
        # Maker paid USDC, received shares -> Maker BUY
        usdc = int(e["makerAmountFilled"]) / 1e6
        shares = int(e["takerAmountFilled"]) / 1e6
        maker_side = "BUY"
        taker_side = "SELL"
    else:
        # Maker paid shares, received USDC -> Maker SELL
        shares = int(e["makerAmountFilled"]) / 1e6
        usdc = int(e["takerAmountFilled"]) / 1e6
        maker_side = "SELL"
        taker_side = "BUY"

    price = usdc / shares if shares > 0 else 0
    side = maker_side if is_maker else taker_side
    role = "maker" if is_maker else "taker"

    return {
        "tx_hash": e["transactionHash"],
        "timestamp": int(e["timestamp"]),
        "outcome": outcome,
        "side": side,
        "role": role,
        "shares": shares,
        "usdc": usdc,
        "price": price,
        "maker": e["maker"],
        "taker": e["taker"],
        "makerAssetId": e["makerAssetId"][:20] + "..." if len(e["makerAssetId"]) > 20 else e["makerAssetId"]
    }


def main():
    print("=" * 80)
    print("DEBUG: SELL trades in Goldsky")
    print("=" * 80)
    print()

    # Fetch all events
    print("Fetching events where wallet is MAKER...")
    maker_events = fetch_goldsky_maker_events()
    print(f"  Found: {len(maker_events)}")

    print("Fetching events where wallet is TAKER...")
    taker_events = fetch_goldsky_taker_events()
    print(f"  Found: {len(taker_events)}")
    print()

    # Parse and find SELL trades
    all_trades = []

    for e in maker_events:
        parsed = parse_event(e, TARGET_WALLET)
        if parsed:
            all_trades.append(parsed)

    for e in taker_events:
        parsed = parse_event(e, TARGET_WALLET)
        if parsed:
            all_trades.append(parsed)

    # Filter to BTC market only
    btc_trades = [t for t in all_trades if t["outcome"] in ["Up", "Down"]]

    # Separate BUY and SELL
    buys = [t for t in btc_trades if t["side"] == "BUY"]
    sells = [t for t in btc_trades if t["side"] == "SELL"]

    print(f"Total BTC market trades: {len(btc_trades)}")
    print(f"  BUY trades: {len(buys)}")
    print(f"  SELL trades: {len(sells)}")
    print()

    if sells:
        print("=" * 80)
        print("SELL TRADES FOUND:")
        print("=" * 80)
        print()
        print(f"{'Time':<10} {'Side':<5} {'Role':<6} {'Out':<5} {'Shares':>10} {'USDC':>10} {'Price':>8}")
        print("-" * 70)

        for t in sells[:20]:
            time_str = datetime.utcfromtimestamp(t["timestamp"]).strftime("%H:%M:%S")
            print(f"{time_str:<10} {t['side']:<5} {t['role']:<6} {t['outcome']:<5} {t['shares']:>10.2f} {t['usdc']:>10.2f} {t['price']:>8.4f}")

        print()
        print("Sample TX hashes to verify on PolygonScan:")
        for t in sells[:5]:
            print(f"  https://polygonscan.com/tx/{t['tx_hash']}")

        print()
        print("=" * 80)
        print("KEY INSIGHT:")
        print("=" * 80)

        # Analyze SELL trades
        maker_sells = [t for t in sells if t["role"] == "maker"]
        taker_sells = [t for t in sells if t["role"] == "taker"]

        print(f"SELL as MAKER: {len(maker_sells)} trades")
        print(f"SELL as TAKER: {len(taker_sells)} trades")
        print()

        if taker_sells:
            print("When wallet is TAKER and side=SELL:")
            print("  -> Wallet is SELLING to someone else's BUY order")
            print("  -> Wallet gives shares, receives USDC")
            print()
            print("This happens when:")
            print("  - Someone posts a BUY limit order")
            print("  - Our wallet hits that order (taker) by selling into it")


if __name__ == "__main__":
    main()
