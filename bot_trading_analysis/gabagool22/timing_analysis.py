#!/usr/bin/env python3
"""
Timing Analysis: How does gabagool22 buy both UP and DOWN for < $1?
"""

import json
import os
from datetime import datetime
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def analyze_timing(market_slug):
    """Analyze the timing of UP vs DOWN purchases"""

    filepath = os.path.join(DATA_DIR, f"{market_slug}.json")
    with open(filepath, 'r') as f:
        data = json.load(f)

    trades = data['trades']
    winner = data['winning_outcome'].upper()

    print(f"\n{'='*80}")
    print(f"TIMING ANALYSIS: {market_slug}")
    print(f"Winner: {winner} | Total Trades: {len(trades)}")
    print(f"{'='*80}")

    # Group trades by timestamp (same second)
    by_timestamp = defaultdict(list)
    for t in trades:
        by_timestamp[t['timestamp']].append(t)

    print(f"\nUnique timestamps: {len(by_timestamp)}")
    print(f"Avg trades per second: {len(trades) / len(by_timestamp):.1f}")

    # Analyze transactions (same tx_hash = atomic operation)
    by_tx = defaultdict(list)
    for t in trades:
        by_tx[t['tx_hash']].append(t)

    print(f"\nUnique transactions: {len(by_tx)}")
    print(f"Avg trades per transaction: {len(trades) / len(by_tx):.1f}")

    # Find transactions that have BOTH UP and DOWN
    dual_side_txs = []
    for tx_hash, tx_trades in by_tx.items():
        outcomes = set(t['outcome'].upper() for t in tx_trades)
        if 'UP' in outcomes and 'DOWN' in outcomes:
            dual_side_txs.append((tx_hash, tx_trades))

    print(f"\n{'='*80}")
    print(f"DUAL-SIDE TRANSACTIONS (UP + DOWN in same tx)")
    print(f"{'='*80}")
    print(f"Found: {len(dual_side_txs)} transactions with both UP and DOWN")
    print(f"Percentage: {len(dual_side_txs) / len(by_tx) * 100:.1f}% of all transactions")

    # Analyze a few dual-side transactions in detail
    print(f"\n--- Sample Dual-Side Transactions ---\n")

    for i, (tx_hash, tx_trades) in enumerate(dual_side_txs[:5]):
        print(f"Transaction {i+1}: {tx_hash[:20]}...")

        up_cost = 0
        down_cost = 0
        up_shares = 0
        down_shares = 0

        for t in tx_trades:
            outcome = t['outcome'].upper()
            side = t['side']

            if side == 'BUY':
                if outcome == 'UP':
                    up_cost += t['usdc']
                    up_shares += t['shares']
                else:
                    down_cost += t['usdc']
                    down_shares += t['shares']
            else:  # SELL
                if outcome == 'UP':
                    up_cost -= t['usdc']
                    up_shares -= t['shares']
                else:
                    down_cost -= t['usdc']
                    down_shares -= t['shares']

        total_cost = up_cost + down_cost
        min_shares = min(up_shares, down_shares) if up_shares > 0 and down_shares > 0 else 0

        print(f"  UP:   {up_shares:>8.2f} shares @ ${up_cost:>8.2f}")
        print(f"  DOWN: {down_shares:>8.2f} shares @ ${down_cost:>8.2f}")
        print(f"  TOTAL COST: ${total_cost:.2f}")
        if min_shares > 0:
            cost_per_pair = total_cost / min_shares
            print(f"  COST PER PAIR: ${cost_per_pair:.4f} (guaranteed $1 payout)")
            if cost_per_pair < 1:
                print(f"  >>> PROFIT LOCKED: ${(1 - cost_per_pair) * min_shares:.2f}")
            else:
                print(f"  >>> LOSS LOCKED: ${(cost_per_pair - 1) * min_shares:.2f}")
        print()

    # Analyze timing gaps between UP and DOWN buys
    print(f"\n{'='*80}")
    print(f"TIMING GAP ANALYSIS")
    print(f"{'='*80}")

    # Get all BUY trades
    up_buys = [(t['timestamp'], t['shares'], t['price'], t['usdc'])
               for t in trades if t['side'] == 'BUY' and t['outcome'].upper() == 'UP']
    down_buys = [(t['timestamp'], t['shares'], t['price'], t['usdc'])
                 for t in trades if t['side'] == 'BUY' and t['outcome'].upper() == 'DOWN']

    print(f"\nUP buys: {len(up_buys)}")
    print(f"DOWN buys: {len(down_buys)}")

    # Find matching pairs (same timestamp)
    up_by_ts = defaultdict(list)
    down_by_ts = defaultdict(list)

    for ts, shares, price, usdc in up_buys:
        up_by_ts[ts].append((shares, price, usdc))
    for ts, shares, price, usdc in down_buys:
        down_by_ts[ts].append((shares, price, usdc))

    # Count same-second pairs
    same_second = 0
    different_second = 0

    for ts in up_by_ts:
        if ts in down_by_ts:
            same_second += 1
        else:
            different_second += 1

    print(f"\nTimestamps with BOTH UP and DOWN buys: {same_second}")
    print(f"Timestamps with only UP buys: {different_second}")
    print(f"Timestamps with only DOWN buys: {len(down_by_ts) - same_second}")

    # Calculate average prices
    avg_up_price = sum(p for _, _, p, _ in up_buys) / len(up_buys) if up_buys else 0
    avg_down_price = sum(p for _, _, p, _ in down_buys) / len(down_buys) if down_buys else 0

    print(f"\n{'='*80}")
    print(f"PRICE ANALYSIS")
    print(f"{'='*80}")
    print(f"\nAverage BUY prices:")
    print(f"  UP:   ${avg_up_price:.4f}")
    print(f"  DOWN: ${avg_down_price:.4f}")
    print(f"  SUM:  ${avg_up_price + avg_down_price:.4f}")

    if avg_up_price + avg_down_price < 1:
        print(f"\n  >>> AVERAGE SPREAD CAPTURE: ${1 - (avg_up_price + avg_down_price):.4f} per share pair")
    else:
        print(f"\n  >>> AVERAGE SPREAD LOSS: ${(avg_up_price + avg_down_price) - 1:.4f} per share pair")

    # Show chronological trade sequence
    print(f"\n{'='*80}")
    print(f"FIRST 30 TRADES (Chronological)")
    print(f"{'='*80}\n")

    print(f"{'Time':<12} {'Side':<6} {'Outcome':<6} {'Shares':>10} {'Price':>8} {'USDC':>10} {'Role':<6}")
    print("-" * 70)

    for t in trades[:30]:
        dt = datetime.fromtimestamp(t['timestamp'])
        time_str = dt.strftime("%H:%M:%S")
        print(f"{time_str:<12} {t['side']:<6} {t['outcome']:<6} {t['shares']:>10.2f} ${t['price']:>6.4f} ${t['usdc']:>9.2f} {t['role']:<6}")

    # Analyze a specific second in detail
    print(f"\n{'='*80}")
    print(f"DETAILED SECOND-BY-SECOND BREAKDOWN")
    print(f"{'='*80}")

    # Find a busy second
    busiest_ts = max(by_timestamp.keys(), key=lambda ts: len(by_timestamp[ts]))
    busiest_trades = by_timestamp[busiest_ts]

    dt = datetime.fromtimestamp(busiest_ts)
    print(f"\nBusiest second: {dt.strftime('%H:%M:%S')} ({len(busiest_trades)} trades)")
    print()

    up_in_second = [t for t in busiest_trades if t['outcome'].upper() == 'UP']
    down_in_second = [t for t in busiest_trades if t['outcome'].upper() == 'DOWN']

    print(f"UP trades in this second: {len(up_in_second)}")
    for t in up_in_second:
        print(f"  {t['side']} {t['shares']:.2f} @ ${t['price']:.4f} ({t['role']})")

    print(f"\nDOWN trades in this second: {len(down_in_second)}")
    for t in down_in_second:
        print(f"  {t['side']} {t['shares']:.2f} @ ${t['price']:.4f} ({t['role']})")

def main():
    # Analyze all available markets
    market_files = [f.replace('.json', '') for f in os.listdir(DATA_DIR)
                    if f.endswith('.json') and 'updown' in f]

    for market_slug in sorted(market_files)[:1]:  # Analyze first one in detail
        analyze_timing(market_slug)

if __name__ == "__main__":
    main()
