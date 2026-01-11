#!/usr/bin/env python3
"""
Visualize gabagool22's pricing algorithm
"""

import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from collections import defaultdict
import numpy as np
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "114_market_analysis")

with open('data/btc-updown-15m-1768037400.json', 'r') as f:
    data = json.load(f)

trades = data['trades']
maker_trades = [t for t in trades if t['role'] == 'maker']

fig = plt.figure(figsize=(16, 12))
fig.suptitle('gabagool22 Pricing Algorithm Analysis\nHow They Decide Limit Order Prices',
             fontsize=14, fontweight='bold')

# =========================================================================
# Chart 1: Price Tracking Over Time
# =========================================================================
ax1 = fig.add_subplot(2, 2, 1)

# Get market prices (from all trades)
up_market = [(datetime.fromtimestamp(t['timestamp']), t['price'])
             for t in trades if t['outcome'].upper() == 'UP']
down_market = [(datetime.fromtimestamp(t['timestamp']), t['price'])
               for t in trades if t['outcome'].upper() == 'DOWN']

# Get gabagool22's limit order prices
up_limit = [(datetime.fromtimestamp(t['timestamp']), t['price'])
            for t in maker_trades if t['outcome'].upper() == 'UP']
down_limit = [(datetime.fromtimestamp(t['timestamp']), t['price'])
              for t in maker_trades if t['outcome'].upper() == 'DOWN']

if up_market:
    times, prices = zip(*up_market)
    ax1.scatter(times, prices, c='lightgreen', alpha=0.3, s=10, label='UP market price')

if down_market:
    times, prices = zip(*down_market)
    ax1.scatter(times, prices, c='lightcoral', alpha=0.3, s=10, label='DOWN market price')

if up_limit:
    times, prices = zip(*up_limit)
    ax1.scatter(times, prices, c='green', alpha=0.8, s=30, marker='s', label='gabagool22 UP limit')

if down_limit:
    times, prices = zip(*down_limit)
    ax1.scatter(times, prices, c='red', alpha=0.8, s=30, marker='s', label='gabagool22 DOWN limit')

ax1.set_title('Market Price vs gabagool22 Limit Orders\n(Squares = their limit orders)')
ax1.set_xlabel('Time')
ax1.set_ylabel('Price ($)')
ax1.legend(loc='upper right', fontsize=8)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# =========================================================================
# Chart 2: Order Size Distribution
# =========================================================================
ax2 = fig.add_subplot(2, 2, 2)

sizes = [t['shares'] for t in maker_trades]
bins = np.arange(0, 30, 2)
ax2.hist(sizes, bins=bins, alpha=0.7, color='blue', edgecolor='black')
ax2.axvline(x=26, color='red', linestyle='--', linewidth=2, label='Max size: 26 shares')
ax2.axvline(x=np.median(sizes), color='orange', linestyle='-', linewidth=2, label=f'Median: {np.median(sizes):.0f} shares')

ax2.set_title(f'Order Size Distribution\n(Most common: 26 shares = likely max order size)')
ax2.set_xlabel('Order Size (shares)')
ax2.set_ylabel('Frequency')
ax2.legend()
ax2.grid(True, alpha=0.3)

# =========================================================================
# Chart 3: UP+DOWN Sum When Both Posted
# =========================================================================
ax3 = fig.add_subplot(2, 2, 3)

# Find seconds where both UP and DOWN were posted
by_ts = defaultdict(list)
for t in maker_trades:
    by_ts[t['timestamp']].append(t)

sums_over_time = []
for ts in sorted(by_ts.keys()):
    ts_trades = by_ts[ts]
    up_prices = [t['price'] for t in ts_trades if t['outcome'].upper() == 'UP']
    down_prices = [t['price'] for t in ts_trades if t['outcome'].upper() == 'DOWN']

    if up_prices and down_prices:
        avg_up = np.mean(up_prices)
        avg_down = np.mean(down_prices)
        sums_over_time.append((datetime.fromtimestamp(ts), avg_up, avg_down, avg_up + avg_down))

if sums_over_time:
    times = [s[0] for s in sums_over_time]
    up_vals = [s[1] for s in sums_over_time]
    down_vals = [s[2] for s in sums_over_time]
    total_vals = [s[3] for s in sums_over_time]

    ax3.plot(times, up_vals, 'g-', linewidth=1, alpha=0.7, label='UP limit price')
    ax3.plot(times, down_vals, 'r-', linewidth=1, alpha=0.7, label='DOWN limit price')
    ax3.plot(times, total_vals, 'b-', linewidth=2, label='UP + DOWN sum')
    ax3.axhline(y=1.0, color='black', linestyle='--', linewidth=2, label='$1.00 breakeven')

    # Color regions
    ax3.fill_between(times, total_vals, 1.0, where=[v < 1.0 for v in total_vals],
                     alpha=0.3, color='green', label='Profit zone')
    ax3.fill_between(times, total_vals, 1.0, where=[v >= 1.0 for v in total_vals],
                     alpha=0.3, color='red', label='Loss zone')

ax3.set_title('Complementary Pricing: UP + DOWN Sum Over Time\n(They adjust BOTH to keep sum near $0.98-$1.00)')
ax3.set_xlabel('Time')
ax3.set_ylabel('Price ($)')
ax3.legend(loc='upper right', fontsize=8)
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax3.set_ylim(0, 1.2)

# =========================================================================
# Chart 4: Price Level Heatmap
# =========================================================================
ax4 = fig.add_subplot(2, 2, 4)

# Create price buckets
price_buckets = defaultdict(lambda: {'up': 0, 'down': 0})
for t in maker_trades:
    bucket = round(t['price'] * 20) / 20  # Round to nearest 0.05
    if t['outcome'].upper() == 'UP':
        price_buckets[bucket]['up'] += 1
    else:
        price_buckets[bucket]['down'] += 1

prices = sorted(price_buckets.keys())
up_counts = [price_buckets[p]['up'] for p in prices]
down_counts = [price_buckets[p]['down'] for p in prices]

x = np.arange(len(prices))
width = 0.35

bars1 = ax4.bar(x - width/2, up_counts, width, label='UP orders', color='green', alpha=0.7)
bars2 = ax4.bar(x + width/2, down_counts, width, label='DOWN orders', color='red', alpha=0.7)

ax4.set_xlabel('Price Level')
ax4.set_ylabel('Number of Orders')
ax4.set_title('Where They Place Limit Orders\n(UP concentrated high, DOWN concentrated low)')
ax4.set_xticks(x[::2])
ax4.set_xticklabels([f'${p:.2f}' for p in prices[::2]], rotation=45)
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'pricing_algorithm.png'), dpi=150, bbox_inches='tight')
print(f"Saved: {os.path.join(OUTPUT_DIR, 'pricing_algorithm.png')}")
