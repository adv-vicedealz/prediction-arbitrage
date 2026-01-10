#!/usr/bin/env python3
"""
Fetch wallet trades for BTC Up/Down market (Jan 9, 3:00PM-3:15PM ET) using Goldsky Subgraph.

Market: https://polymarket.com/event/btc-updown-15m-1767988800/btc-updown-15m-1767988800
"""
import requests
import json
from datetime import datetime

ENDPOINT = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"

# Wallet to analyze
WALLET = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"

# BTC Up/Down market token IDs (Jan 9, 3:00PM-3:15PM ET)
UP_TOKEN = "20098822806699786608925683741990259325965587907700151964325722685695053007834"
DOWN_TOKEN = "3301490775101477737989979692484641795753004523012443272673048938214823516392"
TOKEN_IDS = [UP_TOKEN, DOWN_TOKEN]

# Time range - market window is 3:00PM-3:15PM ET on Jan 9
# Fetch wider range to capture all trading activity around this market
START_TS = 1767913200  # Jan 9, 2026 00:00:00 UTC
END_TS = 1767999600    # Jan 10, 2026 00:00:00 UTC


def fetch_trades_by_role(wallet: str, role: str, start_ts: int, end_ts: int) -> list:
    """
    Fetch all trades where wallet was maker or taker.
    Uses cursor-based pagination to bypass 1000 record limit.
    """
    wallet = wallet.lower()
    all_trades = []
    last_id = ""
    batch_num = 0

    while True:
        batch_num += 1

        where = f'{role}: "{wallet}", timestamp_gte: "{start_ts}", timestamp_lt: "{end_ts}"'
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

        resp = requests.post(ENDPOINT, json={"query": query}, timeout=30)
        data = resp.json()

        if "errors" in data:
            print(f"Error: {data['errors']}")
            break

        events = data["data"]["orderFilledEvents"]
        if not events:
            break

        all_trades.extend(events)
        last_id = events[-1]["id"]

        print(f"  {role.capitalize()} batch {batch_num}: {len(events)} trades (total: {len(all_trades)})")

        if len(events) < 1000:
            break

    return all_trades


def filter_by_market(trades: list, token_ids: list) -> list:
    """Filter trades to only include those for specific token IDs."""
    filtered = []
    for t in trades:
        if t["makerAssetId"] in token_ids or t["takerAssetId"] in token_ids:
            filtered.append(t)
    return filtered


def parse_trade(trade: dict, wallet: str) -> dict:
    """Parse a trade into the requested output format."""
    wallet = wallet.lower()
    ts = int(trade["timestamp"])
    dt = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    is_maker = trade["maker"].lower() == wallet

    # Determine side and amounts
    if trade["makerAssetId"] == "0":
        # Maker paid USDC, received shares = BUY for maker
        if is_maker:
            side = "BUY"
        else:
            side = "SELL"  # Taker sold shares
        usdc = int(trade["makerAmountFilled"]) / 1e6
        shares = int(trade["takerAmountFilled"]) / 1e6
        token_id = trade["takerAssetId"]
    else:
        # Maker paid shares, received USDC = SELL for maker
        if is_maker:
            side = "SELL"
        else:
            side = "BUY"  # Taker bought shares
        shares = int(trade["makerAmountFilled"]) / 1e6
        usdc = int(trade["takerAmountFilled"]) / 1e6
        token_id = trade["makerAssetId"]

    price = usdc / shares if shares > 0 else 0
    fee = int(trade["fee"]) / 1e6

    # Determine outcome
    if token_id == UP_TOKEN:
        outcome = "Up"
    elif token_id == DOWN_TOKEN:
        outcome = "Down"
    else:
        outcome = "Unknown"

    return {
        "timestamp": dt,
        "unix_ts": ts,
        "side": side,
        "outcome": outcome,
        "shares": round(shares, 2),
        "usdc": round(usdc, 2),
        "price": round(price, 4),
        "fee": round(fee, 6),
        "role": "maker" if is_maker else "taker",
        "tx": trade["transactionHash"]
    }


def analyze_trades(parsed_trades: list) -> dict:
    """Analyze trading activity."""
    if not parsed_trades:
        return {"error": "No trades found"}

    # Group by side and outcome
    buys_up = [t for t in parsed_trades if t["side"] == "BUY" and t["outcome"] == "Up"]
    sells_up = [t for t in parsed_trades if t["side"] == "SELL" and t["outcome"] == "Up"]
    buys_down = [t for t in parsed_trades if t["side"] == "BUY" and t["outcome"] == "Down"]
    sells_down = [t for t in parsed_trades if t["side"] == "SELL" and t["outcome"] == "Down"]

    maker_trades = [t for t in parsed_trades if t["role"] == "maker"]
    taker_trades = [t for t in parsed_trades if t["role"] == "taker"]

    total_fees = sum(t["fee"] for t in parsed_trades)

    # Calculate net positions
    up_shares_bought = sum(t["shares"] for t in buys_up)
    up_shares_sold = sum(t["shares"] for t in sells_up)
    down_shares_bought = sum(t["shares"] for t in buys_down)
    down_shares_sold = sum(t["shares"] for t in sells_down)

    up_usdc_spent = sum(t["usdc"] for t in buys_up)
    up_usdc_received = sum(t["usdc"] for t in sells_up)
    down_usdc_spent = sum(t["usdc"] for t in buys_down)
    down_usdc_received = sum(t["usdc"] for t in sells_down)

    # Time analysis
    timestamps = [t["unix_ts"] for t in parsed_trades]
    first_trade = datetime.utcfromtimestamp(min(timestamps)).strftime("%Y-%m-%d %H:%M:%S")
    last_trade = datetime.utcfromtimestamp(max(timestamps)).strftime("%Y-%m-%d %H:%M:%S")
    duration_mins = (max(timestamps) - min(timestamps)) / 60

    # Average prices
    avg_buy_up = sum(t["price"] * t["shares"] for t in buys_up) / up_shares_bought if up_shares_bought > 0 else 0
    avg_sell_up = sum(t["price"] * t["shares"] for t in sells_up) / up_shares_sold if up_shares_sold > 0 else 0
    avg_buy_down = sum(t["price"] * t["shares"] for t in buys_down) / down_shares_bought if down_shares_bought > 0 else 0
    avg_sell_down = sum(t["price"] * t["shares"] for t in sells_down) / down_shares_sold if down_shares_sold > 0 else 0

    return {
        "summary": {
            "total_trades": len(parsed_trades),
            "maker_trades": len(maker_trades),
            "taker_trades": len(taker_trades),
            "total_fees": round(total_fees, 2),
            "first_trade": first_trade,
            "last_trade": last_trade,
            "duration_mins": round(duration_mins, 2)
        },
        "up_outcome": {
            "buys": len(buys_up),
            "sells": len(sells_up),
            "shares_bought": round(up_shares_bought, 2),
            "shares_sold": round(up_shares_sold, 2),
            "net_position": round(up_shares_bought - up_shares_sold, 2),
            "usdc_spent": round(up_usdc_spent, 2),
            "usdc_received": round(up_usdc_received, 2),
            "net_usdc": round(up_usdc_received - up_usdc_spent, 2),
            "avg_buy_price": round(avg_buy_up, 4),
            "avg_sell_price": round(avg_sell_up, 4)
        },
        "down_outcome": {
            "buys": len(buys_down),
            "sells": len(sells_down),
            "shares_bought": round(down_shares_bought, 2),
            "shares_sold": round(down_shares_sold, 2),
            "net_position": round(down_shares_bought - down_shares_sold, 2),
            "usdc_spent": round(down_usdc_spent, 2),
            "usdc_received": round(down_usdc_received, 2),
            "net_usdc": round(down_usdc_received - down_usdc_spent, 2),
            "avg_buy_price": round(avg_buy_down, 4),
            "avg_sell_price": round(avg_sell_down, 4)
        },
        "volume": {
            "total_usdc": round(up_usdc_spent + up_usdc_received + down_usdc_spent + down_usdc_received, 2),
            "total_shares": round(up_shares_bought + up_shares_sold + down_shares_bought + down_shares_sold, 2)
        }
    }


if __name__ == "__main__":
    print(f"Fetching trades for wallet: {WALLET}")
    print(f"Market: BTC Up/Down - Jan 9, 3:00PM-3:15PM ET")
    print(f"Token IDs: Up={UP_TOKEN[:20]}..., Down={DOWN_TOKEN[:20]}...")
    print()

    # Fetch all trades
    print("Fetching maker trades...")
    maker_trades = fetch_trades_by_role(WALLET, "maker", START_TS, END_TS)

    print("\nFetching taker trades...")
    taker_trades = fetch_trades_by_role(WALLET, "taker", START_TS, END_TS)

    all_trades = maker_trades + taker_trades
    print(f"\nTotal trades fetched: {len(all_trades)}")

    # Filter by market
    market_trades = filter_by_market(all_trades, TOKEN_IDS)
    print(f"Trades on this market: {len(market_trades)}")

    if not market_trades:
        print("\nNo trades found for this wallet on this market.")
        exit(0)

    # Parse trades
    parsed = [parse_trade(t, WALLET) for t in market_trades]
    parsed.sort(key=lambda x: x["unix_ts"])

    # Analyze
    analysis = analyze_trades(parsed)

    # Print results
    print("\n" + "="*60)
    print("ANALYSIS RESULTS")
    print("="*60)

    print("\nSUMMARY:")
    s = analysis["summary"]
    print(f"  Total trades: {s['total_trades']}")
    print(f"  Maker trades: {s['maker_trades']} ({100*s['maker_trades']/s['total_trades']:.1f}%)")
    print(f"  Taker trades: {s['taker_trades']} ({100*s['taker_trades']/s['total_trades']:.1f}%)")
    print(f"  Total fees paid: ${s['total_fees']:.2f}")
    print(f"  First trade: {s['first_trade']} UTC")
    print(f"  Last trade: {s['last_trade']} UTC")
    print(f"  Duration: {s['duration_mins']:.2f} minutes")

    print("\nUP OUTCOME:")
    u = analysis["up_outcome"]
    print(f"  Buys: {u['buys']} trades, {u['shares_bought']:.2f} shares @ avg ${u['avg_buy_price']:.4f}")
    print(f"  Sells: {u['sells']} trades, {u['shares_sold']:.2f} shares @ avg ${u['avg_sell_price']:.4f}")
    print(f"  Net position: {u['net_position']:.2f} shares")
    print(f"  USDC: spent ${u['usdc_spent']:.2f}, received ${u['usdc_received']:.2f}, net ${u['net_usdc']:.2f}")

    print("\nDOWN OUTCOME:")
    d = analysis["down_outcome"]
    print(f"  Buys: {d['buys']} trades, {d['shares_bought']:.2f} shares @ avg ${d['avg_buy_price']:.4f}")
    print(f"  Sells: {d['sells']} trades, {d['shares_sold']:.2f} shares @ avg ${d['avg_sell_price']:.4f}")
    print(f"  Net position: {d['net_position']:.2f} shares")
    print(f"  USDC: spent ${d['usdc_spent']:.2f}, received ${d['usdc_received']:.2f}, net ${d['net_usdc']:.2f}")

    print("\nVOLUME:")
    v = analysis["volume"]
    print(f"  Total USDC traded: ${v['total_usdc']:.2f}")
    print(f"  Total shares traded: {v['total_shares']:.2f}")

    # Save detailed trades
    output_file = "/Users/mattiacostola/claude/prediction-arbitrage/data/btc_updown_analysis/trades_1767988800.json"
    with open(output_file, "w") as f:
        json.dump({
            "wallet": WALLET,
            "market": "BTC Up/Down - Jan 9, 3:00PM-3:15PM ET",
            "market_url": "https://polymarket.com/event/btc-updown-15m-1767988800/btc-updown-15m-1767988800",
            "condition_id": "0xa6f95944775d53dcb4fa395ea2b2569174a66ad516f375c679319fb4c1c5018b",
            "token_ids": {"up": UP_TOKEN, "down": DOWN_TOKEN},
            "analysis": analysis,
            "trades": parsed
        }, f, indent=2)
    print(f"\nDetailed trades saved to: {output_file}")

    # Print sample trades
    print("\nSAMPLE TRADES (first 5):")
    print("-" * 100)
    print(f"{'Timestamp':<20} {'Side':<6} {'Outcome':<6} {'Shares':>10} {'USDC':>10} {'Price':>8} {'Fee':>10} {'Role':<6}")
    print("-" * 100)
    for t in parsed[:5]:
        print(f"{t['timestamp']:<20} {t['side']:<6} {t['outcome']:<6} {t['shares']:>10.2f} {t['usdc']:>10.2f} {t['price']:>8.4f} {t['fee']:>10.6f} {t['role']:<6}")
