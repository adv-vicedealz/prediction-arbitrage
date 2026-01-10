#!/usr/bin/env python3
"""
Visualize the timing and cost basis of gabagool22's trades
"""

import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from collections import defaultdict
import numpy as np
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "114_market_analysis")

# Load market data
with open('data/btc-updown-15m-1768037400.json', 'r') as f:
    data = json.load(f)

trades = data['trades']
winner = data['winning_outcome'].upper()

# Process trades
timeline = []
cumulative_up = 0
cumulative_down = 0
cumulative_up_cost = 0
cumulative_down_cost = 0

for t in trades:
    dt = datetime.fromtimestamp(t['timestamp'])
    outcome = t['outcome'].upper()
    side = t['side']

    if side == 'BUY':
        if outcome == 'UP':
            cumulative_up += t['shares']
            cumulative_up_cost += t['usdc']
        else:
            cumulative_down += t['shares']
            cumulative_down_cost += t['usdc']
    else:
        if outcome == 'UP':
            cumulative_up -= t['shares']
        else:
            cumulative_down -= t['shares']

    timeline.append({
        'dt': dt,
        'timestamp': t['timestamp'],
        'outcome': outcome,
        'side': side,
        'price': t['price'],
        'shares': t['shares'],
        'role': t['role'],
        'up_held': cumulative_up,
        'down_held': cumulative_down,
        'up_cost': cumulative_up_cost,
        'down_cost': cumulative_down_cost
    })

# Create figure
fig = plt.figure(figsize=(16, 12))
fig.suptitle('gabagool22 Trading Mechanics: How They Buy Both Sides\nbtc-updown-15m-1768037400',
             fontsize=14, fontweight='bold')

# =========================================================================
# Chart 1: Price Evolution - UP vs DOWN
# =========================================================================
ax1 = fig.add_subplot(2, 2, 1)

up_trades = [(t['dt'], t['price']) for t in timeline if t['outcome'] == 'UP']
down_trades = [(t['dt'], t['price']) for t in timeline if t['outcome'] == 'DOWN']

up_times, up_prices = zip(*up_trades)
down_times, down_prices = zip(*down_trades)

ax1.scatter(up_times, up_prices, c='green', alpha=0.3, s=5, label='UP price')
ax1.scatter(down_times, down_prices, c='red', alpha=0.3, s=5, label='DOWN price')

# Add UP+DOWN sum line (smoothed)
combined = []
for i, t in enumerate(timeline):
    # Find nearest UP and DOWN prices
    up_p = [x['price'] for x in timeline[max(0,i-5):i+1] if x['outcome'] == 'UP']
    down_p = [x['price'] for x in timeline[max(0,i-5):i+1] if x['outcome'] == 'DOWN']
    if up_p and down_p:
        combined.append((t['dt'], np.mean(up_p) + np.mean(down_p)))

if combined:
    c_times, c_prices = zip(*combined)
    ax1.plot(c_times, c_prices, 'b-', linewidth=2, label='UP+DOWN sum', alpha=0.7)
    ax1.axhline(y=1.0, color='black', linestyle='--', linewidth=1, label='$1.00 (breakeven)')

ax1.set_title('Price Evolution: When UP+DOWN < $1, Profit is Possible')
ax1.set_xlabel('Time')
ax1.set_ylabel('Price ($)')
ax1.legend(loc='upper right')
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# =========================================================================
# Chart 2: When do they buy UP vs DOWN?
# =========================================================================
ax2 = fig.add_subplot(2, 2, 2)

buy_up = [(t['dt'], t['shares']) for t in timeline if t['side'] == 'BUY' and t['outcome'] == 'UP']
buy_down = [(t['dt'], t['shares']) for t in timeline if t['side'] == 'BUY' and t['outcome'] == 'DOWN']

if buy_up:
    bu_times, bu_shares = zip(*buy_up)
    ax2.scatter(bu_times, bu_shares, c='green', alpha=0.5, s=20, label=f'BUY UP ({len(buy_up)} trades)')

if buy_down:
    bd_times, bd_shares = zip(*buy_down)
    ax2.scatter(bd_times, [-s for s in bd_shares], c='red', alpha=0.5, s=20, label=f'BUY DOWN ({len(buy_down)} trades)')

ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.set_title('Buy Activity: UP (positive) vs DOWN (negative)')
ax2.set_xlabel('Time')
ax2.set_ylabel('Shares Bought')
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# =========================================================================
# Chart 3: Cumulative Position Balance
# =========================================================================
ax3 = fig.add_subplot(2, 2, 3)

times = [t['dt'] for t in timeline]
up_held = [t['up_held'] for t in timeline]
down_held = [t['down_held'] for t in timeline]
balance = [t['up_held'] - t['down_held'] for t in timeline]

ax3.fill_between(times, up_held, alpha=0.3, color='green', label='UP shares held')
ax3.fill_between(times, down_held, alpha=0.3, color='red', label='DOWN shares held')
ax3.plot(times, balance, 'b-', linewidth=2, label='Balance (UP-DOWN)')
ax3.axhline(y=0, color='black', linestyle='--', linewidth=1)

ax3.set_title('Position Building: Trying to Stay Balanced')
ax3.set_xlabel('Time')
ax3.set_ylabel('Shares')
ax3.legend(loc='upper left')
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# =========================================================================
# Chart 4: Maker vs Taker by Time
# =========================================================================
ax4 = fig.add_subplot(2, 2, 4)

# Group by 30-second windows
start_ts = timeline[0]['timestamp']
windows = defaultdict(lambda: {'maker': 0, 'taker': 0})

for t in timeline:
    window = (t['timestamp'] - start_ts) // 30
    windows[window][t['role']] += 1

window_nums = sorted(windows.keys())
makers = [windows[w]['maker'] for w in window_nums]
takers = [windows[w]['taker'] for w in window_nums]
times_30s = [w * 30 / 60 for w in window_nums]  # Convert to minutes

ax4.bar(times_30s, makers, width=0.4, alpha=0.7, color='blue', label='Maker (limit orders)')
ax4.bar(times_30s, takers, width=0.4, alpha=0.7, color='orange', bottom=makers, label='Taker (market orders)')

ax4.set_title(f'Order Type by 30-Second Windows (Maker: {sum(makers)/(sum(makers)+sum(takers))*100:.1f}%)')
ax4.set_xlabel('Time (minutes)')
ax4.set_ylabel('Number of Trades')
ax4.legend(loc='upper right')
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()

# Save
output_path = os.path.join(OUTPUT_DIR, "timing_mechanics.png")
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"Saved: {output_path}")

# =========================================================================
# Create second figure: Cost Basis Analysis
# =========================================================================
fig2 = plt.figure(figsize=(16, 8))
fig2.suptitle('Cost Basis Analysis: How gabagool22 Captures Spread', fontsize=14, fontweight='bold')

# Chart 1: Running Average Cost Basis
ax1 = fig2.add_subplot(1, 2, 1)

# Calculate running average cost
running_up_cost = []
running_down_cost = []
running_combined = []
total_up_shares = 0
total_down_shares = 0
total_up_cost = 0
total_down_cost = 0

for t in timeline:
    if t['side'] == 'BUY':
        if t['outcome'] == 'UP':
            total_up_shares += t['shares']
            total_up_cost += t['shares'] * t['price']
        else:
            total_down_shares += t['shares']
            total_down_cost += t['shares'] * t['price']

    up_avg = total_up_cost / total_up_shares if total_up_shares > 0 else 0
    down_avg = total_down_cost / total_down_shares if total_down_shares > 0 else 0

    running_up_cost.append(up_avg)
    running_down_cost.append(down_avg)
    running_combined.append(up_avg + down_avg if up_avg > 0 and down_avg > 0 else None)

times = [t['dt'] for t in timeline]
ax1.plot(times, running_up_cost, 'g-', linewidth=1.5, label='Avg UP cost', alpha=0.7)
ax1.plot(times, running_down_cost, 'r-', linewidth=1.5, label='Avg DOWN cost', alpha=0.7)

# Filter None values for combined
combined_times = [t for t, c in zip(times, running_combined) if c is not None]
combined_values = [c for c in running_combined if c is not None]
ax1.plot(combined_times, combined_values, 'b-', linewidth=2, label='Combined (UP+DOWN)')

ax1.axhline(y=1.0, color='black', linestyle='--', linewidth=2, label='$1.00 breakeven')
ax1.axhline(y=0.5, color='gray', linestyle=':', linewidth=1)

ax1.fill_between(combined_times, combined_values, 1.0,
                  where=[c < 1.0 for c in combined_values],
                  alpha=0.3, color='green', label='Spread captured')
ax1.fill_between(combined_times, combined_values, 1.0,
                  where=[c >= 1.0 for c in combined_values],
                  alpha=0.3, color='red', label='Spread paid')

ax1.set_title('Running Average Cost Basis')
ax1.set_xlabel('Time')
ax1.set_ylabel('Average Cost ($)')
ax1.legend(loc='upper right', fontsize=8)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax1.set_ylim(0, 1.2)

# Chart 2: Histogram of combined purchase prices
ax2 = fig2.add_subplot(1, 2, 2)

# Find matched pairs (UP + DOWN in same second)
by_second = defaultdict(lambda: {'up': [], 'down': []})
for t in trades:
    if t['side'] == 'BUY':
        by_second[t['timestamp']][t['outcome'].lower()].append(t['price'])

combined_prices = []
for ts, prices in by_second.items():
    if prices['up'] and prices['down']:
        # Average price in that second
        avg_up = np.mean(prices['up'])
        avg_down = np.mean(prices['down'])
        combined_prices.append(avg_up + avg_down)

if combined_prices:
    bins = np.arange(0.8, 1.3, 0.02)
    n, bins_out, patches = ax2.hist(combined_prices, bins=bins, alpha=0.7, edgecolor='black')

    # Color bars based on profit/loss
    for patch, left_edge in zip(patches, bins_out[:-1]):
        if left_edge < 1.0:
            patch.set_facecolor('green')
        else:
            patch.set_facecolor('red')

    ax2.axvline(x=1.0, color='black', linestyle='--', linewidth=2, label='$1.00 breakeven')
    ax2.axvline(x=np.mean(combined_prices), color='blue', linestyle='-', linewidth=2,
                label=f'Mean: ${np.mean(combined_prices):.4f}')

    below_1 = sum(1 for p in combined_prices if p < 1.0)
    above_1 = sum(1 for p in combined_prices if p >= 1.0)

    ax2.set_title(f'Distribution of Combined Prices (Same-Second Buys)\n'
                  f'Below 1.00: {below_1} ({below_1/len(combined_prices)*100:.1f}%) | '
                  f'Above 1.00: {above_1} ({above_1/len(combined_prices)*100:.1f}%)')
    ax2.set_xlabel('Combined Price (UP + DOWN)')
    ax2.set_ylabel('Frequency')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

plt.tight_layout()

output_path2 = os.path.join(OUTPUT_DIR, "cost_basis_analysis.png")
plt.savefig(output_path2, dpi=150, bbox_inches='tight')
print(f"Saved: {output_path2}")
