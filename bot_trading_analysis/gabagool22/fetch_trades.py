"""
Fetch and save trade data for gabagool22.
Wallet: 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d
Market: btc-updown-15m-1768037400
"""

import sys
import os
import json
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bot_identifier.market_fetcher import (
    fetch_market_metadata,
    fetch_and_parse_market_trades
)

# Configuration
TARGET_WALLET = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
MARKET_SLUG = "btc-updown-15m-1768037400"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def main():
    print("=" * 60)
    print("FETCHING TRADES FOR GABAGOOL22")
    print("=" * 60)
    print(f"Wallet: {TARGET_WALLET}")
    print(f"Market: {MARKET_SLUG}")
    print()

    # Fetch market metadata
    print("Fetching market metadata...")
    market = fetch_market_metadata(MARKET_SLUG)
    if not market:
        print("ERROR: Could not fetch market metadata")
        return

    print(f"  Question: {market.question}")
    print(f"  Winner: {market.winning_outcome}")
    print()

    # Fetch all trades
    print("Fetching all trades from Goldsky...")
    all_trades = fetch_and_parse_market_trades(market)
    print(f"  Total trades in market: {len(all_trades)}")

    # Filter for target wallet
    wallet_trades = [t for t in all_trades if t.wallet == TARGET_WALLET.lower()]
    print(f"  Trades for gabagool22: {len(wallet_trades)}")
    print()

    # Sort by timestamp
    wallet_trades.sort(key=lambda t: (t.timestamp, t.id))

    # Convert to serializable format
    trades_data = []
    for t in wallet_trades:
        trades_data.append({
            "id": t.id,
            "timestamp": t.timestamp,
            "datetime": datetime.fromtimestamp(t.timestamp).isoformat(),
            "side": t.side,
            "outcome": t.outcome,
            "shares": t.shares,
            "usdc": t.usdc,
            "price": t.price,
            "role": t.role,
            "tx_hash": t.tx_hash,
            "fee": t.fee
        })

    # Save to JSON
    output_data = {
        "wallet": TARGET_WALLET,
        "market_slug": MARKET_SLUG,
        "market_question": market.question,
        "winning_outcome": market.winning_outcome,
        "total_trades": len(trades_data),
        "fetched_at": datetime.now().isoformat(),
        "trades": trades_data
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"{MARKET_SLUG}.json")

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Saved {len(trades_data)} trades to {output_file}")

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Calculate totals
    up_bought = sum(t["shares"] for t in trades_data if t["outcome"] == "Up" and t["side"] == "BUY")
    up_sold = sum(t["shares"] for t in trades_data if t["outcome"] == "Up" and t["side"] == "SELL")
    down_bought = sum(t["shares"] for t in trades_data if t["outcome"] == "Down" and t["side"] == "BUY")
    down_sold = sum(t["shares"] for t in trades_data if t["outcome"] == "Down" and t["side"] == "SELL")

    up_cost = sum(t["usdc"] for t in trades_data if t["outcome"] == "Up" and t["side"] == "BUY")
    up_rev = sum(t["usdc"] for t in trades_data if t["outcome"] == "Up" and t["side"] == "SELL")
    down_cost = sum(t["usdc"] for t in trades_data if t["outcome"] == "Down" and t["side"] == "BUY")
    down_rev = sum(t["usdc"] for t in trades_data if t["outcome"] == "Down" and t["side"] == "SELL")

    maker_count = sum(1 for t in trades_data if t["role"] == "maker")
    taker_count = sum(1 for t in trades_data if t["role"] == "taker")

    print(f"UP: Bought {up_bought:.2f} shares @ ${up_cost/up_bought:.4f} avg = ${up_cost:.2f}")
    print(f"UP: Sold {up_sold:.2f} shares @ ${up_rev/up_sold:.4f} avg = ${up_rev:.2f}")
    print(f"UP Net: {up_bought - up_sold:.2f} shares")
    print()
    print(f"DOWN: Bought {down_bought:.2f} shares @ ${down_cost/down_bought:.4f} avg = ${down_cost:.2f}")
    print(f"DOWN: Sold {down_sold:.2f} shares @ ${down_rev/down_sold:.4f} avg = ${down_rev:.2f}")
    print(f"DOWN Net: {down_bought - down_sold:.2f} shares")
    print()

    # P&L
    up_net = up_bought - up_sold
    total_cost = up_cost + down_cost
    total_rev = up_rev + down_rev
    payout = max(0, up_net) * 1.0 if market.winning_outcome == "up" else 0
    pnl = payout + total_rev - total_cost

    print(f"Resolution payout ({market.winning_outcome} wins): ${payout:.2f}")
    print(f"Net P&L: ${pnl:.2f}")
    print()
    print(f"Maker: {maker_count} ({100*maker_count/len(trades_data):.1f}%)")
    print(f"Taker: {taker_count} ({100*taker_count/len(trades_data):.1f}%)")

    # Timing
    first_ts = trades_data[0]["timestamp"]
    last_ts = trades_data[-1]["timestamp"]
    duration = (last_ts - first_ts) / 60
    print(f"Duration: {duration:.1f} minutes")
    print(f"Trades/minute: {len(trades_data)/duration:.1f}")


if __name__ == "__main__":
    main()
