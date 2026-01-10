#!/usr/bin/env python3
"""
Deep Strategy Analysis for gabagool22
Visualizes trading patterns, position building, and P&L mechanics
"""

import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
import numpy as np

# Configure paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_trade_data(market_slug):
    """Load trade data from JSON file"""
    filepath = os.path.join(DATA_DIR, f"{market_slug}.json")
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_single_market(data):
    """Comprehensive analysis of a single market"""
    trades = data['trades']
    winner = data['winning_outcome'].upper()
    market_slug = data['market_slug']
    question = data['market_question']

    print(f"\n{'='*70}")
    print(f"DEEP STRATEGY ANALYSIS: gabagool22")
    print(f"{'='*70}")
    print(f"Market: {market_slug}")
    print(f"Question: {question}")
    print(f"Winner: {winner}")
    print(f"Total Trades: {len(trades)}")

    # Convert timestamps to datetime
    for t in trades:
        t['dt'] = datetime.fromtimestamp(t['timestamp'])

    # Sort by timestamp
    trades.sort(key=lambda x: (x['timestamp'], x['id']))

    # Calculate time span
    start_time = trades[0]['dt']
    end_time = trades[-1]['dt']
    duration = (end_time - start_time).total_seconds() / 60
    print(f"Duration: {duration:.1f} minutes")
    print(f"Trades/minute: {len(trades)/max(duration, 1):.1f}")

    # Analyze each trade and build time series
    timeline = []
    cumulative = {
        'up_shares': 0, 'down_shares': 0,
        'up_cost': 0, 'down_cost': 0,
        'up_revenue': 0, 'down_revenue': 0,
        'maker_count': 0, 'taker_count': 0
    }

    # Price tracking
    up_prices = []
    down_prices = []

    for t in trades:
        outcome = t['outcome'].upper()
        side = t['side']
        shares = t['shares']
        usdc = t['usdc']
        price = t['price']
        role = t['role']

        # Track prices
        if outcome == 'UP':
            up_prices.append((t['dt'], price))
        else:
            down_prices.append((t['dt'], price))

        # Update position
        if side == 'BUY':
            if outcome == 'UP':
                cumulative['up_shares'] += shares
                cumulative['up_cost'] += usdc
            else:
                cumulative['down_shares'] += shares
                cumulative['down_cost'] += usdc
        else:  # SELL
            if outcome == 'UP':
                cumulative['up_shares'] -= shares
                cumulative['up_revenue'] += usdc
            else:
                cumulative['down_shares'] -= shares
                cumulative['down_revenue'] += usdc

        if role == 'maker':
            cumulative['maker_count'] += 1
        else:
            cumulative['taker_count'] += 1

        # Calculate current P&L (assuming market resolves to winner)
        if winner == 'UP':
            payout = cumulative['up_shares'] * 1.0  # UP shares pay $1
            # DOWN shares pay $0
        else:
            payout = cumulative['down_shares'] * 1.0  # DOWN shares pay $1
            # UP shares pay $0

        total_cost = cumulative['up_cost'] + cumulative['down_cost']
        total_revenue = cumulative['up_revenue'] + cumulative['down_revenue']
        pnl = payout + total_revenue - total_cost

        timeline.append({
            'dt': t['dt'],
            'timestamp': t['timestamp'],
            'side': side,
            'outcome': outcome,
            'shares': shares,
            'price': price,
            'role': role,
            'usdc': usdc,
            'up_shares': cumulative['up_shares'],
            'down_shares': cumulative['down_shares'],
            'net_position': cumulative['up_shares'] - cumulative['down_shares'],
            'up_cost': cumulative['up_cost'],
            'down_cost': cumulative['down_cost'],
            'pnl': pnl
        })

    return timeline, up_prices, down_prices, data

def create_visualizations(timeline, up_prices, down_prices, data):
    """Create comprehensive strategy visualizations"""

    market_slug = data['market_slug']
    winner = data['winning_outcome'].upper()

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 14))
    fig.suptitle(f'gabagool22 Trading Strategy Analysis\n{market_slug} (Winner: {winner})',
                 fontsize=14, fontweight='bold')

    # =========================================================================
    # CHART 1: Price Timeline with Trade Markers
    # =========================================================================
    ax1 = fig.add_subplot(3, 2, 1)

    # Plot UP prices
    if up_prices:
        up_times, up_vals = zip(*up_prices)
        ax1.scatter(up_times, up_vals, c='green', alpha=0.3, s=10, label='UP price')

    # Plot DOWN prices
    if down_prices:
        down_times, down_vals = zip(*down_prices)
        ax1.scatter(down_times, down_vals, c='red', alpha=0.3, s=10, label='DOWN price')

    # Add buy/sell markers for large trades
    large_trades = [t for t in timeline if t['shares'] > 50]
    for t in large_trades[:50]:  # Limit to avoid clutter
        color = 'blue' if t['side'] == 'BUY' else 'orange'
        marker = '^' if t['side'] == 'BUY' else 'v'
        ax1.scatter([t['dt']], [t['price']], c=color, marker=marker, s=100,
                   edgecolor='black', linewidth=0.5, zorder=5)

    ax1.set_title('Price Evolution with Trade Markers')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Price ($)')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # =========================================================================
    # CHART 2: Position Evolution (UP vs DOWN shares)
    # =========================================================================
    ax2 = fig.add_subplot(3, 2, 2)

    times = [t['dt'] for t in timeline]
    up_shares = [t['up_shares'] for t in timeline]
    down_shares = [t['down_shares'] for t in timeline]

    ax2.fill_between(times, up_shares, alpha=0.5, color='green', label='UP shares')
    ax2.fill_between(times, down_shares, alpha=0.5, color='red', label='DOWN shares')
    ax2.plot(times, up_shares, 'g-', linewidth=1)
    ax2.plot(times, down_shares, 'r-', linewidth=1)

    ax2.set_title('Position Evolution: UP vs DOWN Holdings')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Shares Held')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # =========================================================================
    # CHART 3: Net Position (UP - DOWN)
    # =========================================================================
    ax3 = fig.add_subplot(3, 2, 3)

    net_pos = [t['net_position'] for t in timeline]
    colors = ['green' if p > 0 else 'red' for p in net_pos]

    ax3.fill_between(times, net_pos, 0, where=[p > 0 for p in net_pos],
                     alpha=0.5, color='green', label='Long UP (bullish)')
    ax3.fill_between(times, net_pos, 0, where=[p <= 0 for p in net_pos],
                     alpha=0.5, color='red', label='Long DOWN (bearish)')
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax3.plot(times, net_pos, 'b-', linewidth=1, alpha=0.7)

    # Mark winner
    ax3.text(0.02, 0.98, f'Winner: {winner}', transform=ax3.transAxes,
             fontsize=12, fontweight='bold', verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

    ax3.set_title('Net Position (UP shares - DOWN shares)')
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Net Shares')
    ax3.legend(loc='lower right')
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # =========================================================================
    # CHART 4: Cumulative P&L
    # =========================================================================
    ax4 = fig.add_subplot(3, 2, 4)

    pnls = [t['pnl'] for t in timeline]
    colors = ['green' if p > 0 else 'red' for p in pnls]

    ax4.fill_between(times, pnls, 0, where=[p > 0 for p in pnls],
                     alpha=0.5, color='green')
    ax4.fill_between(times, pnls, 0, where=[p <= 0 for p in pnls],
                     alpha=0.5, color='red')
    ax4.plot(times, pnls, 'b-', linewidth=1.5)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)

    final_pnl = pnls[-1]
    ax4.text(0.98, 0.98, f'Final P&L: ${final_pnl:.2f}', transform=ax4.transAxes,
             fontsize=12, fontweight='bold', verticalalignment='top',
             horizontalalignment='right',
             bbox=dict(boxstyle='round',
                      facecolor='green' if final_pnl > 0 else 'red',
                      alpha=0.8))

    ax4.set_title('Cumulative P&L Over Time')
    ax4.set_xlabel('Time')
    ax4.set_ylabel('P&L ($)')
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # =========================================================================
    # CHART 5: Trade Distribution by Price Level
    # =========================================================================
    ax5 = fig.add_subplot(3, 2, 5)

    # Group trades by price bucket
    buy_up = [t['price'] for t in timeline if t['side'] == 'BUY' and t['outcome'] == 'UP']
    sell_up = [t['price'] for t in timeline if t['side'] == 'SELL' and t['outcome'] == 'UP']
    buy_down = [t['price'] for t in timeline if t['side'] == 'BUY' and t['outcome'] == 'DOWN']
    sell_down = [t['price'] for t in timeline if t['side'] == 'SELL' and t['outcome'] == 'DOWN']

    bins = np.arange(0, 1.05, 0.05)

    ax5.hist(buy_up, bins=bins, alpha=0.5, color='green', label=f'BUY UP ({len(buy_up)})', density=True)
    ax5.hist(sell_up, bins=bins, alpha=0.5, color='lightgreen', label=f'SELL UP ({len(sell_up)})', density=True)
    ax5.hist(buy_down, bins=bins, alpha=0.5, color='red', label=f'BUY DOWN ({len(buy_down)})', density=True)
    ax5.hist(sell_down, bins=bins, alpha=0.5, color='salmon', label=f'SELL DOWN ({len(sell_down)})', density=True)

    ax5.axvline(x=0.5, color='black', linestyle='--', linewidth=1, label='Fair value')
    ax5.set_title('Trade Distribution by Price Level')
    ax5.set_xlabel('Price ($)')
    ax5.set_ylabel('Density')
    ax5.legend(loc='upper right', fontsize=8)
    ax5.grid(True, alpha=0.3)

    # =========================================================================
    # CHART 6: Maker vs Taker Analysis
    # =========================================================================
    ax6 = fig.add_subplot(3, 2, 6)

    # Separate by role
    maker_trades = [t for t in timeline if t['role'] == 'maker']
    taker_trades = [t for t in timeline if t['role'] == 'taker']

    maker_pnl = sum(t['shares'] * (1 if t['outcome'] == winner else 0) if t['side'] == 'BUY'
                   else -t['shares'] * (1 if t['outcome'] == winner else 0)
                   for t in maker_trades)
    taker_pnl = sum(t['shares'] * (1 if t['outcome'] == winner else 0) if t['side'] == 'BUY'
                   else -t['shares'] * (1 if t['outcome'] == winner else 0)
                   for t in taker_trades)

    # Bar chart
    roles = ['Maker\n(Limit Orders)', 'Taker\n(Market Orders)']
    counts = [len(maker_trades), len(taker_trades)]
    maker_pct = len(maker_trades) / len(timeline) * 100

    bars = ax6.bar(roles, counts, color=['blue', 'orange'], alpha=0.7)
    ax6.set_title(f'Order Type Distribution (Maker: {maker_pct:.1f}%)')
    ax6.set_ylabel('Number of Trades')

    # Add count labels
    for bar, count in zip(bars, counts):
        ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                str(count), ha='center', fontsize=12, fontweight='bold')

    ax6.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # Save figure
    output_path = os.path.join(OUTPUT_DIR, f"strategy_deep_dive_{market_slug.split('-')[-1]}.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved: {output_path}")

    return output_path

def print_strategy_summary(timeline, data):
    """Print detailed strategy summary"""

    winner = data['winning_outcome'].upper()

    # Calculate metrics
    final = timeline[-1]

    print(f"\n{'='*70}")
    print("STRATEGY MECHANICS")
    print(f"{'='*70}")

    # Position summary
    print(f"\n1. FINAL POSITIONS:")
    print(f"   UP shares:   {final['up_shares']:.2f}")
    print(f"   DOWN shares: {final['down_shares']:.2f}")
    print(f"   Net bias:    {'BULLISH' if final['net_position'] > 0 else 'BEARISH'} ({abs(final['net_position']):.2f} shares)")
    print(f"   Winner was:  {winner}")
    print(f"   Correct?:    {'YES' if (final['net_position'] > 0 and winner == 'UP') or (final['net_position'] < 0 and winner == 'DOWN') else 'NO'}")

    # Cost summary
    print(f"\n2. COST BREAKDOWN:")
    print(f"   UP cost:     ${final['up_cost']:.2f}")
    print(f"   DOWN cost:   ${final['down_cost']:.2f}")
    print(f"   Total cost:  ${final['up_cost'] + final['down_cost']:.2f}")

    # Payout calculation
    print(f"\n3. PAYOUT CALCULATION:")
    if winner == 'UP':
        payout = final['up_shares'] * 1.0
        print(f"   UP pays $1 each:   {final['up_shares']:.2f} × $1 = ${payout:.2f}")
        print(f"   DOWN pays $0 each: {final['down_shares']:.2f} × $0 = $0.00")
    else:
        payout = final['down_shares'] * 1.0
        print(f"   UP pays $0 each:   {final['up_shares']:.2f} × $0 = $0.00")
        print(f"   DOWN pays $1 each: {final['down_shares']:.2f} × $1 = ${payout:.2f}")

    print(f"   Total payout: ${payout:.2f}")

    # P&L
    total_revenue = sum(t['usdc'] for t in data['trades'] if t['side'] == 'SELL')
    total_cost = final['up_cost'] + final['down_cost']
    pnl = payout + total_revenue - total_cost

    print(f"\n4. P&L CALCULATION:")
    print(f"   + Payout:     ${payout:.2f}")
    print(f"   + Revenue:    ${total_revenue:.2f} (from selling shares)")
    print(f"   - Cost:       ${total_cost:.2f}")
    print(f"   ─────────────────")
    print(f"   = Net P&L:    ${pnl:.2f}")

    # Maker/Taker
    maker_count = sum(1 for t in data['trades'] if t['role'] == 'maker')
    taker_count = sum(1 for t in data['trades'] if t['role'] == 'taker')

    print(f"\n5. ORDER TYPE:")
    print(f"   Maker orders: {maker_count} ({maker_count/len(data['trades'])*100:.1f}%)")
    print(f"   Taker orders: {taker_count} ({taker_count/len(data['trades'])*100:.1f}%)")

    # Average prices
    buy_up_prices = [t['price'] for t in data['trades'] if t['side'] == 'BUY' and t['outcome'].upper() == 'UP']
    sell_up_prices = [t['price'] for t in data['trades'] if t['side'] == 'SELL' and t['outcome'].upper() == 'UP']
    buy_down_prices = [t['price'] for t in data['trades'] if t['side'] == 'BUY' and t['outcome'].upper() == 'DOWN']
    sell_down_prices = [t['price'] for t in data['trades'] if t['side'] == 'SELL' and t['outcome'].upper() == 'DOWN']

    print(f"\n6. AVERAGE PRICES:")
    if buy_up_prices:
        print(f"   Avg BUY UP price:    ${np.mean(buy_up_prices):.4f}")
    if sell_up_prices:
        print(f"   Avg SELL UP price:   ${np.mean(sell_up_prices):.4f}")
    if buy_down_prices:
        print(f"   Avg BUY DOWN price:  ${np.mean(buy_down_prices):.4f}")
    if sell_down_prices:
        print(f"   Avg SELL DOWN price: ${np.mean(sell_down_prices):.4f}")

    # Strategy interpretation
    print(f"\n{'='*70}")
    print("STRATEGY INTERPRETATION")
    print(f"{'='*70}")

    print("""
gabagool22 operates as a DELTA-NEUTRAL MARKET MAKER:

1. CORE STRATEGY:
   • Posts limit orders on BOTH sides of the market (UP and DOWN)
   • Tries to maintain roughly equal positions in both outcomes
   • Captures the bid-ask spread when orders get filled

2. HOW IT WORKS:
   • If UP is trading at $0.51 bid / $0.53 ask
   • And DOWN is trading at $0.47 bid / $0.49 ask
   • gabagool22 posts orders to buy BOTH at favorable prices
   • When both fill: pays $0.51 + $0.47 = $0.98 for guaranteed $1 payout
   • Profit = $0.02 per "round trip"

3. WHY 80% MAKER:
   • Maker orders (limit orders) capture the spread
   • Taker orders (market orders) pay the spread
   • High maker ratio = maximizing spread capture

4. RISK FACTORS:
   • INVENTORY RISK: If positions get imbalanced, exposed to direction
   • ADVERSE SELECTION: Smart traders may pick off stale quotes
   • VOLATILITY: Fast moves can leave orders unfilled on one side

5. THIS MARKET SPECIFICALLY:
""")

    if pnl > 0:
        print(f"   ✓ PROFITABLE: Made ${pnl:.2f}")
        print(f"   ✓ Likely captured spread effectively")
    else:
        print(f"   ✗ LOSS: Lost ${abs(pnl):.2f}")
        if (final['net_position'] > 0 and winner == 'DOWN') or (final['net_position'] < 0 and winner == 'UP'):
            print(f"   ✗ Position was biased AGAINST the winner")
            print(f"   ✗ Inventory risk materialized - couldn't stay delta-neutral")

    print()

def main():
    # Analyze all available market files
    market_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json') and 'updown' in f]

    if not market_files:
        print("No market data files found!")
        return

    print(f"Found {len(market_files)} market data files")

    # Analyze each market
    for market_file in sorted(market_files):
        market_slug = market_file.replace('.json', '')
        print(f"\nAnalyzing: {market_slug}")

        try:
            data = load_trade_data(market_slug)
            timeline, up_prices, down_prices, data = analyze_single_market(data)
            create_visualizations(timeline, up_prices, down_prices, data)
            print_strategy_summary(timeline, data)
        except Exception as e:
            print(f"Error analyzing {market_slug}: {e}")

if __name__ == "__main__":
    main()
