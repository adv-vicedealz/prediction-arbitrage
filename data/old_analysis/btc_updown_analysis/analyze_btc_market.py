#!/usr/bin/env python3
"""
Analyze wallet activity on BTC Up/Down market.
"""
import json
from datetime import datetime
from collections import defaultdict

WALLET = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
UP_TOKEN = "65689469986114736683609567440585706468061828613693669084008270331829703859210"
DOWN_TOKEN = "19004630472054155562446266004006762878910712196312117007145993767241545797916"

# Load all trade files
files = {
    "maker_buy_down": "/tmp/maker_buy_down.json",
    "maker_sell_down": "/tmp/maker_sell_down.json",
    "taker_buy_down": "/tmp/taker_buy_down.json",
    "taker_sell_down": "/tmp/taker_sell_down.json",
    "maker_buy_up": "/tmp/maker_buy_up.json",
    "maker_sell_up": "/tmp/maker_sell_up.json",
    "taker_buy_up": "/tmp/taker_buy_up.json",
    "taker_sell_up": "/tmp/taker_sell_up.json",
}

all_trades = []

for trade_type, filepath in files.items():
    with open(filepath, "r") as f:
        data = json.load(f)
        events = data.get("data", {}).get("orderFilledEvents", [])
        for e in events:
            e["_trade_type"] = trade_type
        all_trades.extend(events)

print(f"Total trades loaded: {len(all_trades)}")

# Parse and categorize trades
parsed_trades = []

for t in all_trades:
    trade_type = t["_trade_type"]
    ts = int(t["timestamp"])
    dt = datetime.utcfromtimestamp(ts)

    is_maker = "maker" in trade_type

    # Determine side, token, and amounts based on trade type
    if "buy" in trade_type:
        side = "BUY"
        if is_maker:
            # Maker bought: paid USDC (makerAmount), received shares (takerAmount)
            usdc = int(t["makerAmountFilled"]) / 1e6
            shares = int(t["takerAmountFilled"]) / 1e6
            token_id = t["takerAssetId"]
        else:
            # Taker bought: maker paid shares, taker paid USDC
            usdc = int(t["takerAmountFilled"]) / 1e6
            shares = int(t["makerAmountFilled"]) / 1e6
            token_id = t["makerAssetId"]
    else:
        side = "SELL"
        if is_maker:
            # Maker sold: paid shares, received USDC
            shares = int(t["makerAmountFilled"]) / 1e6
            usdc = int(t["takerAmountFilled"]) / 1e6
            token_id = t["makerAssetId"]
        else:
            # Taker sold: taker paid shares (takerAmount), received USDC (makerAmount)
            shares = int(t["takerAmountFilled"]) / 1e6
            usdc = int(t["makerAmountFilled"]) / 1e6
            token_id = t["takerAssetId"]

    price = usdc / shares if shares > 0 else 0
    fee = int(t.get("fee", "0")) / 1e6

    outcome = "Up" if token_id == UP_TOKEN else "Down" if token_id == DOWN_TOKEN else "Unknown"

    parsed_trades.append({
        "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "unix_ts": ts,
        "side": side,
        "outcome": outcome,
        "shares": shares,
        "usdc": usdc,
        "price": price,
        "fee": fee,
        "role": "maker" if is_maker else "taker",
        "tx": t["transactionHash"][:20] + "..."
    })

# Sort by timestamp
parsed_trades.sort(key=lambda x: x["unix_ts"])

print(f"Parsed trades: {len(parsed_trades)}")

# Analysis
print("\n" + "="*70)
print("WALLET ACTIVITY ANALYSIS")
print("="*70)
print(f"Wallet: {WALLET}")
print(f"Market: BTC Up/Down - Jan 9, 6:00AM-6:15AM ET")
print(f"Resolution: Up = $1.00, Down = $0.00")
print("="*70)

# Summary stats
maker_trades = [t for t in parsed_trades if t["role"] == "maker"]
taker_trades = [t for t in parsed_trades if t["role"] == "taker"]

total_fees = sum(t["fee"] for t in parsed_trades)

print(f"\n📊 SUMMARY:")
print(f"  Total trades: {len(parsed_trades)}")
print(f"  Maker trades: {len(maker_trades)} ({100*len(maker_trades)/len(parsed_trades):.1f}%)")
print(f"  Taker trades: {len(taker_trades)} ({100*len(taker_trades)/len(parsed_trades):.1f}%)")
print(f"  Total fees paid: ${total_fees:.2f}")

if parsed_trades:
    print(f"  First trade: {parsed_trades[0]['timestamp']} UTC")
    print(f"  Last trade: {parsed_trades[-1]['timestamp']} UTC")
    duration_mins = (parsed_trades[-1]["unix_ts"] - parsed_trades[0]["unix_ts"]) / 60
    print(f"  Duration: {duration_mins:.2f} minutes")

# By outcome
for outcome in ["Up", "Down"]:
    print(f"\n📈 {outcome.upper()} OUTCOME:")

    buys = [t for t in parsed_trades if t["side"] == "BUY" and t["outcome"] == outcome]
    sells = [t for t in parsed_trades if t["side"] == "SELL" and t["outcome"] == outcome]

    shares_bought = sum(t["shares"] for t in buys)
    shares_sold = sum(t["shares"] for t in sells)
    usdc_spent = sum(t["usdc"] for t in buys)
    usdc_received = sum(t["usdc"] for t in sells)

    avg_buy = sum(t["price"] * t["shares"] for t in buys) / shares_bought if shares_bought > 0 else 0
    avg_sell = sum(t["price"] * t["shares"] for t in sells) / shares_sold if shares_sold > 0 else 0

    net_position = shares_bought - shares_sold
    net_usdc = usdc_received - usdc_spent

    print(f"  Buys: {len(buys)} trades, {shares_bought:,.2f} shares @ avg ${avg_buy:.4f}")
    print(f"  Sells: {len(sells)} trades, {shares_sold:,.2f} shares @ avg ${avg_sell:.4f}")
    print(f"  Net position: {net_position:,.2f} shares")
    print(f"  USDC: spent ${usdc_spent:,.2f}, received ${usdc_received:,.2f}, net ${net_usdc:,.2f}")

# P&L Calculation
print("\n" + "="*70)
print("💵 P&L CALCULATION")
print("="*70)

# Up outcome
up_buys = [t for t in parsed_trades if t["side"] == "BUY" and t["outcome"] == "Up"]
up_sells = [t for t in parsed_trades if t["side"] == "SELL" and t["outcome"] == "Up"]
up_shares_bought = sum(t["shares"] for t in up_buys)
up_shares_sold = sum(t["shares"] for t in up_sells)
up_usdc_spent = sum(t["usdc"] for t in up_buys)
up_usdc_received = sum(t["usdc"] for t in up_sells)
up_net_position = up_shares_bought - up_shares_sold

# Down outcome
down_buys = [t for t in parsed_trades if t["side"] == "BUY" and t["outcome"] == "Down"]
down_sells = [t for t in parsed_trades if t["side"] == "SELL" and t["outcome"] == "Down"]
down_shares_bought = sum(t["shares"] for t in down_buys)
down_shares_sold = sum(t["shares"] for t in down_sells)
down_usdc_spent = sum(t["usdc"] for t in down_buys)
down_usdc_received = sum(t["usdc"] for t in down_sells)
down_net_position = down_shares_bought - down_shares_sold

# Resolution values
UP_RESOLUTION = 1.0  # Market resolved to Up
DOWN_RESOLUTION = 0.0

# P&L = (final position * resolution price) - USDC spent + USDC received
up_pnl = (up_net_position * UP_RESOLUTION) - up_usdc_spent + up_usdc_received
down_pnl = (down_net_position * DOWN_RESOLUTION) - down_usdc_spent + down_usdc_received

total_pnl = up_pnl + down_pnl - total_fees

print(f"\nUp Position:")
print(f"  Shares held at resolution: {up_net_position:,.2f}")
print(f"  Resolution value (@ $1.00): ${up_net_position * UP_RESOLUTION:,.2f}")
print(f"  Total USDC spent buying: ${up_usdc_spent:,.2f}")
print(f"  Total USDC received selling: ${up_usdc_received:,.2f}")
print(f"  Up P&L: ${up_pnl:,.2f}")

print(f"\nDown Position:")
print(f"  Shares held at resolution: {down_net_position:,.2f}")
print(f"  Resolution value (@ $0.00): ${down_net_position * DOWN_RESOLUTION:,.2f}")
print(f"  Total USDC spent buying: ${down_usdc_spent:,.2f}")
print(f"  Total USDC received selling: ${down_usdc_received:,.2f}")
print(f"  Down P&L: ${down_pnl:,.2f}")

print(f"\n{'='*40}")
print(f"  Up P&L:      ${up_pnl:>12,.2f}")
print(f"  Down P&L:    ${down_pnl:>12,.2f}")
print(f"  Fees:        ${-total_fees:>12,.2f}")
print(f"  {'='*28}")
print(f"  TOTAL P&L:   ${total_pnl:>12,.2f}")
print(f"{'='*40}")

# Volume analysis
total_volume = up_usdc_spent + up_usdc_received + down_usdc_spent + down_usdc_received
print(f"\n💰 VOLUME:")
print(f"  Total USDC volume: ${total_volume:,.2f}")
print(f"  Total shares traded: {up_shares_bought + up_shares_sold + down_shares_bought + down_shares_sold:,.2f}")

# Trading pattern analysis
print("\n📊 TRADING PATTERN ANALYSIS:")

# Time distribution
timestamps = [t["unix_ts"] for t in parsed_trades]
if timestamps:
    min_ts = min(timestamps)
    max_ts = max(timestamps)

    # Trades per minute
    duration_mins = (max_ts - min_ts) / 60
    trades_per_min = len(parsed_trades) / duration_mins if duration_mins > 0 else 0
    print(f"  Trading rate: {trades_per_min:.1f} trades/minute")

    # Average trade size
    avg_trade_usdc = total_volume / len(parsed_trades) / 2  # /2 because we count both sides
    avg_trade_shares = (up_shares_bought + up_shares_sold + down_shares_bought + down_shares_sold) / len(parsed_trades) / 2
    print(f"  Avg trade size: ${avg_trade_usdc:.2f} ({avg_trade_shares:.2f} shares)")

# Price analysis
print("\n📈 PRICE ANALYSIS:")
up_buy_prices = [t["price"] for t in up_buys]
up_sell_prices = [t["price"] for t in up_sells]
down_buy_prices = [t["price"] for t in down_buys]
down_sell_prices = [t["price"] for t in down_sells]

if up_buy_prices:
    print(f"  Up buy price range: ${min(up_buy_prices):.4f} - ${max(up_buy_prices):.4f}")
if up_sell_prices:
    print(f"  Up sell price range: ${min(up_sell_prices):.4f} - ${max(up_sell_prices):.4f}")
if down_buy_prices:
    print(f"  Down buy price range: ${min(down_buy_prices):.4f} - ${max(down_buy_prices):.4f}")
if down_sell_prices:
    print(f"  Down sell price range: ${min(down_sell_prices):.4f} - ${max(down_sell_prices):.4f}")

# Check for market making behavior (both sides)
print("\n🔄 MARKET MAKING ANALYSIS:")
is_mm = len(up_buys) > 0 and len(up_sells) > 0
print(f"  Trading both Up sides: {'Yes' if len(up_buys) > 0 and len(up_sells) > 0 else 'No'}")
print(f"  Trading both Down sides: {'Yes' if len(down_buys) > 0 and len(down_sells) > 0 else 'No'}")
print(f"  Trading both outcomes: {'Yes' if (len(up_buys) + len(up_sells) > 0) and (len(down_buys) + len(down_sells) > 0) else 'No'}")

# Counterparty analysis
print("\n👥 COUNTERPARTY ANALYSIS:")
counterparties = set()
for t in all_trades:
    if t["maker"].lower() == WALLET.lower():
        counterparties.add(t["taker"].lower())
    else:
        counterparties.add(t["maker"].lower())
print(f"  Unique counterparties: {len(counterparties)}")

# Save to file
output = {
    "wallet": WALLET,
    "market": "BTC Up/Down - Jan 9, 6:00AM-6:15AM ET",
    "summary": {
        "total_trades": len(parsed_trades),
        "maker_trades": len(maker_trades),
        "taker_trades": len(taker_trades),
        "total_fees": round(total_fees, 2),
        "total_volume": round(total_volume, 2)
    },
    "positions": {
        "up": {
            "shares_bought": round(up_shares_bought, 2),
            "shares_sold": round(up_shares_sold, 2),
            "net_position": round(up_net_position, 2),
            "usdc_spent": round(up_usdc_spent, 2),
            "usdc_received": round(up_usdc_received, 2)
        },
        "down": {
            "shares_bought": round(down_shares_bought, 2),
            "shares_sold": round(down_shares_sold, 2),
            "net_position": round(down_net_position, 2),
            "usdc_spent": round(down_usdc_spent, 2),
            "usdc_received": round(down_usdc_received, 2)
        }
    },
    "pnl": {
        "up_pnl": round(up_pnl, 2),
        "down_pnl": round(down_pnl, 2),
        "fees": round(total_fees, 2),
        "total_pnl": round(total_pnl, 2)
    },
    "trades": parsed_trades
}

with open("/Users/mattiacostola/claude/prediction-arbitrage/data/btc_market_analysis.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Full analysis saved to: data/btc_market_analysis.json")

# Show sample trades
print("\n📜 SAMPLE TRADES (first 10 and last 10):")
print("-" * 100)
print(f"{'Timestamp':<20} {'Side':<6} {'Outcome':<6} {'Shares':>12} {'USDC':>12} {'Price':>8} {'Role':<6}")
print("-" * 100)
for t in parsed_trades[:10]:
    print(f"{t['timestamp']:<20} {t['side']:<6} {t['outcome']:<6} {t['shares']:>12,.2f} {t['usdc']:>12,.2f} {t['price']:>8.4f} {t['role']:<6}")
print("...")
for t in parsed_trades[-10:]:
    print(f"{t['timestamp']:<20} {t['side']:<6} {t['outcome']:<6} {t['shares']:>12,.2f} {t['usdc']:>12,.2f} {t['price']:>8.4f} {t['role']:<6}")
