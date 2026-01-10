"""
Verify trade data for a specific wallet and market.
Fetches raw data from Goldsky and displays in a verifiable format.
"""

import sys
import os

# Add parent directory to path to import bot_identifier
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from bot_identifier.market_fetcher import (
    fetch_market_metadata,
    fetch_and_parse_market_trades
)

# Configuration
TARGET_WALLET = "0x0ea574f3204c5c9c0cdead90392ea0990f4d17e4"
MARKET_SLUG = "btc-updown-15m-1768037400"  # BTC 4:30-4:45AM, winner: UP


def format_timestamp(ts: int) -> str:
    """Convert Unix timestamp to readable format."""
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def main():
    print("=" * 80)
    print(f"TRADE VERIFICATION")
    print(f"Wallet: {TARGET_WALLET}")
    print(f"Market: {MARKET_SLUG}")
    print("=" * 80)
    print()

    # Step 1: Fetch market metadata
    print("Fetching market metadata from Gamma API...")
    market = fetch_market_metadata(MARKET_SLUG)

    if not market:
        print("ERROR: Could not fetch market metadata")
        return

    print(f"  Question: {market.question}")
    print(f"  Resolved: {market.resolved}")
    print(f"  Winner: {market.winning_outcome}")
    print(f"  Token IDs:")
    for outcome, token_id in market.token_ids.items():
        print(f"    {outcome}: {token_id}")
    print()

    # Step 2: Fetch all trades for this market
    print("Fetching trades from Goldsky subgraph...")
    all_trades = fetch_and_parse_market_trades(market)
    print(f"  Total trades in market: {len(all_trades)}")

    # Step 3: Filter for target wallet
    wallet_trades = [t for t in all_trades if t.wallet == TARGET_WALLET.lower()]
    print(f"  Trades for target wallet: {len(wallet_trades)}")
    print()

    if not wallet_trades:
        print("No trades found for this wallet in this market.")
        return

    # Step 4: Sort by timestamp
    wallet_trades.sort(key=lambda t: (t.timestamp, t.id))

    # Step 5: Display each trade
    print("=" * 100)
    print(f"{'Time':<10} {'Side':<5} {'Outcome':<6} {'Shares':>12} {'Price':>8} {'USDC':>12} {'Role':<6} {'TX Hash'}")
    print("-" * 100)

    total_up_bought = 0
    total_up_sold = 0
    total_down_bought = 0
    total_down_sold = 0
    total_up_cost = 0
    total_up_revenue = 0
    total_down_cost = 0
    total_down_revenue = 0

    for trade in wallet_trades:
        time_str = format_timestamp(trade.timestamp)
        tx_short = trade.tx_hash[:16] + "..."

        print(f"{time_str:<10} {trade.side:<5} {trade.outcome:<6} {trade.shares:>12.2f} {trade.price:>8.3f} {trade.usdc:>12.2f} {trade.role:<6} {tx_short}")

        # Accumulate totals
        if trade.outcome == "Up":
            if trade.side == "BUY":
                total_up_bought += trade.shares
                total_up_cost += trade.usdc
            else:
                total_up_sold += trade.shares
                total_up_revenue += trade.usdc
        else:  # Down
            if trade.side == "BUY":
                total_down_bought += trade.shares
                total_down_cost += trade.usdc
            else:
                total_down_sold += trade.shares
                total_down_revenue += trade.usdc

    print("-" * 100)
    print()

    # Step 6: Display summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print(f"Total trades: {len(wallet_trades)}")
    print()
    print("UP OUTCOME:")
    print(f"  Bought: {total_up_bought:.2f} shares @ avg ${total_up_cost/total_up_bought:.3f} = ${total_up_cost:.2f}" if total_up_bought > 0 else "  Bought: 0 shares")
    print(f"  Sold:   {total_up_sold:.2f} shares @ avg ${total_up_revenue/total_up_sold:.3f} = ${total_up_revenue:.2f}" if total_up_sold > 0 else "  Sold:   0 shares")
    print(f"  Net:    {total_up_bought - total_up_sold:.2f} shares")
    print()
    print("DOWN OUTCOME:")
    print(f"  Bought: {total_down_bought:.2f} shares @ avg ${total_down_cost/total_down_bought:.3f} = ${total_down_cost:.2f}" if total_down_bought > 0 else "  Bought: 0 shares")
    print(f"  Sold:   {total_down_sold:.2f} shares @ avg ${total_down_revenue/total_down_sold:.3f} = ${total_down_revenue:.2f}" if total_down_sold > 0 else "  Sold:   0 shares")
    print(f"  Net:    {total_down_bought - total_down_sold:.2f} shares")
    print()

    # P&L calculation
    up_net = total_up_bought - total_up_sold
    down_net = total_down_bought - total_down_sold

    total_cost = total_up_cost + total_down_cost
    total_revenue = total_up_revenue + total_down_revenue

    # Resolution payout (winner is UP)
    if market.winning_outcome == "up":
        resolution_payout = max(0, up_net) * 1.0  # $1 per Up share
    else:
        resolution_payout = max(0, down_net) * 1.0  # $1 per Down share

    pnl = resolution_payout + total_revenue - total_cost

    print("P&L CALCULATION:")
    print(f"  Total cost (buying):    ${total_cost:.2f}")
    print(f"  Total revenue (selling): ${total_revenue:.2f}")
    print(f"  Resolution payout:       ${resolution_payout:.2f} ({market.winning_outcome} wins)")
    print(f"  ---")
    print(f"  Net P&L:                 ${pnl:.2f}")
    print()

    # Role breakdown
    maker_trades = [t for t in wallet_trades if t.role == "maker"]
    taker_trades = [t for t in wallet_trades if t.role == "taker"]
    print(f"Role breakdown: {len(maker_trades)} maker ({100*len(maker_trades)/len(wallet_trades):.1f}%), {len(taker_trades)} taker ({100*len(taker_trades)/len(wallet_trades):.1f}%)")
    print()

    # First and last trade times
    first_trade = wallet_trades[0]
    last_trade = wallet_trades[-1]
    print(f"First trade: {format_timestamp(first_trade.timestamp)}")
    print(f"Last trade:  {format_timestamp(last_trade.timestamp)}")
    print(f"Duration:    {(last_trade.timestamp - first_trade.timestamp)/60:.1f} minutes")


if __name__ == "__main__":
    main()
