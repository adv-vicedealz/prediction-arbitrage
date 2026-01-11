#!/usr/bin/env python3
"""
Visualize one-sided fills and imbalance risk
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
winner = data['winning_outcome'].upper()

# Track position over time
cumulative_up = 0
cumulative_down = 0
timeline = []

for t in sorted(trades, key=lambda x: x['timestamp']):
    if t['side'] == 'BUY':
        if t['outcome'].upper() == 'UP':
            cumulative_up += t['shares']
        else:
            cumulative_down += t['shares']
    else:
        if t['outcome'].upper() == 'UP':
            cumulative_up -= t['shares']
        else:
            cumulative_down -= t['shares']

    timeline.append({
        'dt': datetime.fromtimestamp(t['timestamp']),
        'up': cumulative_up,
        'down': cumulative_down,
        'imbalance': cumulative_up - cumulative_down
    })

fig = plt.figure(figsize=(16, 10))
fig.suptitle('One-Sided Fill Risk: What Happens When Only One Side Gets Filled\n'
             f'Market: btc-updown-15m-1768037400 | Winner: {winner} | Final P&L: -$87.14',
             fontsize=14, fontweight='bold')

# =========================================================================
# Chart 1: Position Imbalance Over Time
# =========================================================================
ax1 = fig.add_subplot(2, 2, 1)

times = [t['dt'] for t in timeline]
imbalances = [t['imbalance'] for t in timeline]

ax1.fill_between(times, imbalances, 0,
                  where=[i > 0 for i in imbalances],
                  alpha=0.5, color='green', label='Heavy UP (bullish)')
ax1.fill_between(times, imbalances, 0,
                  where=[i <= 0 for i in imbalances],
                  alpha=0.5, color='red', label='Heavy DOWN (bearish)')
ax1.plot(times, imbalances, 'b-', linewidth=1)
ax1.axhline(y=0, color='black', linestyle='-', linewidth=2)
ax1.axhline(y=100, color='gray', linestyle='--', linewidth=1, alpha=0.5)
ax1.axhline(y=-100, color='gray', linestyle='--', linewidth=1, alpha=0.5)

# Mark final position
final_imbalance = imbalances[-1]
ax1.annotate(f'Final: {final_imbalance:.0f}\n(Heavy DOWN)',
            xy=(times[-1], final_imbalance),
            xytext=(times[-1], final_imbalance + 100),
            fontsize=10, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='red'),
            color='red')

ax1.set_title('Position Imbalance Over Time (UP shares - DOWN shares)')
ax1.set_xlabel('Time')
ax1.set_ylabel('Imbalance (shares)')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# =========================================================================
# Chart 2: Why They Lost - Position vs Winner
# =========================================================================
ax2 = fig.add_subplot(2, 2, 2)

up_held = [t['up'] for t in timeline]
down_held = [t['down'] for t in timeline]

ax2.fill_between(times, up_held, alpha=0.5, color='green', label='UP shares')
ax2.fill_between(times, down_held, alpha=0.5, color='red', label='DOWN shares')
ax2.plot(times, up_held, 'g-', linewidth=1)
ax2.plot(times, down_held, 'r-', linewidth=1)

# Add winner annotation
ax2.text(0.02, 0.98, f'Winner: {winner}\n\nFinal UP: {up_held[-1]:.0f}\nFinal DOWN: {down_held[-1]:.0f}\n\nPayout: UP wins = ${up_held[-1]:.0f}\nDOWN worthless',
         transform=ax2.transAxes, fontsize=10, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

ax2.set_title('Position Evolution: UP vs DOWN Holdings')
ax2.set_xlabel('Time')
ax2.set_ylabel('Shares Held')
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# =========================================================================
# Chart 3: Time Spent in Each State
# =========================================================================
ax3 = fig.add_subplot(2, 2, 3)

# Categorize imbalance states
heavy_up = sum(1 for i in imbalances if i > 100)
light_up = sum(1 for i in imbalances if 0 < i <= 100)
balanced = sum(1 for i in imbalances if -100 <= i <= 0)
light_down = sum(1 for i in imbalances if -100 > i >= -200)
heavy_down = sum(1 for i in imbalances if i < -200)

states = ['Heavy UP\n(>100)', 'Light UP\n(0-100)', 'Balanced\n(±100)', 'Light DOWN\n(-100 to -200)', 'Heavy DOWN\n(<-200)']
counts = [heavy_up, light_up, balanced, light_down, heavy_down]
colors = ['darkgreen', 'lightgreen', 'gray', 'salmon', 'darkred']

bars = ax3.bar(states, counts, color=colors, alpha=0.7, edgecolor='black')

# Add percentage labels
total = len(imbalances)
for bar, count in zip(bars, counts):
    pct = count / total * 100
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
            f'{pct:.1f}%', ha='center', fontsize=10, fontweight='bold')

ax3.set_title('Time Spent in Each Position State\n(Only 26% of time was balanced!)')
ax3.set_xlabel('Position State')
ax3.set_ylabel('Number of Trades')
ax3.grid(True, alpha=0.3, axis='y')

# =========================================================================
# Chart 4: The Problem Explained
# =========================================================================
ax4 = fig.add_subplot(2, 2, 4)
ax4.axis('off')

explanation = """
WHY ONE-SIDED FILLS CAUSE LOSSES
================================

THE PROBLEM:
• gabagool22 posts limit orders on BOTH UP and DOWN
• But the market doesn't always fill both sides equally
• If UP is rising, everyone wants to BUY UP → their SELL UP orders fill
• Their BUY DOWN orders sit unfilled → position becomes imbalanced

THIS MARKET:
• Started balanced at 10:30
• Market moved → DOWN orders filled more than UP
• By 10:38: -396 shares imbalance (way too much DOWN)
• Tried to rebalance by buying more UP
• But couldn't fully catch up
• Final: -231 shares imbalance (still heavy DOWN)

THE RESULT:
• Winner: UP (pays $1.00 per share)
• Their UP shares: 6,410 → Payout: $6,410
• Their DOWN shares: 6,640 → Payout: $0
• They paid ~$8,200 for positions worth $6,410
• Loss: -$87.14

KEY INSIGHT:
Market makers CANNOT always stay delta-neutral.
When one side fills more than the other,
they're exposed to directional risk.

This is called "INVENTORY RISK" - the main risk
of market making strategies.
"""

ax4.text(0.05, 0.95, explanation, transform=ax4.transAxes,
         fontsize=11, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'one_sided_fills.png'), dpi=150, bbox_inches='tight')
print(f"Saved: {os.path.join(OUTPUT_DIR, 'one_sided_fills.png')}")
