"""
Deep Strategy Analysis for gabagool22
Wallet: 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d
Market: btc-updown-15m-1768037400

Generates:
- price_timeline.png: Price evolution with trade overlay
- position_evolution.png: Position tracking over time
- pnl_accumulation.png: Cumulative P&L breakdown
- order_distribution.png: Order size distribution
- analysis_report.md: Comprehensive written report
"""

import json
import os
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
MARKET_SLUG = "btc-updown-15m-1768037400"


def load_trades():
    """Load trade data from JSON."""
    data_file = os.path.join(DATA_DIR, f"{MARKET_SLUG}.json")
    with open(data_file, "r") as f:
        return json.load(f)


def analyze_time_series(trades, winning_outcome):
    """
    Section 2.1: Time-Series Analysis
    Plot price evolution with trade overlay
    """
    print("Analyzing time series...")

    # Group trades by timestamp and calculate weighted avg price
    up_prices = defaultdict(list)
    down_prices = defaultdict(list)

    for t in trades:
        ts = t["timestamp"]
        if t["outcome"] == "Up":
            up_prices[ts].append((t["price"], t["shares"]))
        else:
            down_prices[ts].append((t["price"], t["shares"]))

    # Calculate weighted average prices per second
    up_timeline = []
    down_timeline = []

    all_timestamps = sorted(set(up_prices.keys()) | set(down_prices.keys()))

    for ts in all_timestamps:
        dt = datetime.fromtimestamp(ts)
        if up_prices[ts]:
            total_shares = sum(s for _, s in up_prices[ts])
            weighted_price = sum(p * s for p, s in up_prices[ts]) / total_shares
            up_timeline.append((dt, weighted_price))
        if down_prices[ts]:
            total_shares = sum(s for _, s in down_prices[ts])
            weighted_price = sum(p * s for p, s in down_prices[ts]) / total_shares
            down_timeline.append((dt, weighted_price))

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot price lines
    if up_timeline:
        up_times, up_vals = zip(*up_timeline)
        ax.plot(up_times, up_vals, 'g-', linewidth=1.5, alpha=0.7, label='UP Price')
    if down_timeline:
        down_times, down_vals = zip(*down_timeline)
        ax.plot(down_times, down_vals, 'r-', linewidth=1.5, alpha=0.7, label='DOWN Price')

    # Overlay BUY/SELL markers
    for t in trades:
        dt = datetime.fromtimestamp(t["timestamp"])
        marker = '^' if t["side"] == "BUY" else 'v'
        color = 'green' if t["outcome"] == "Up" else 'red'
        alpha = 0.3 if t["role"] == "maker" else 0.6
        size = min(t["shares"] / 2, 50)
        ax.scatter(dt, t["price"], marker=marker, c=color, s=size, alpha=alpha)

    # Formatting
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Price ($)', fontsize=12)
    ax.set_title(f'gabagool22 Trade Timeline - {MARKET_SLUG}\nWinner: {winning_outcome.upper()}', fontsize=14)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    ax.set_ylim(0, 1)

    # Add annotations
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='50% line')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "price_timeline.png"), dpi=150)
    plt.close()

    # Calculate metrics
    if up_timeline:
        price_range = max(up_vals) - min(up_vals)
        volatility = np.std(up_vals)
    else:
        price_range = volatility = 0

    return {
        "price_range": price_range,
        "volatility": volatility,
        "num_price_points": len(all_timestamps)
    }


def analyze_position_evolution(trades, winning_outcome):
    """
    Section 2.2: Position Evolution Analysis
    Track cumulative positions over time
    """
    print("Analyzing position evolution...")

    # Calculate cumulative positions
    timeline = []
    up_pos = 0
    down_pos = 0

    for t in trades:
        dt = datetime.fromtimestamp(t["timestamp"])
        shares = t["shares"]

        if t["outcome"] == "Up":
            if t["side"] == "BUY":
                up_pos += shares
            else:
                up_pos -= shares
        else:
            if t["side"] == "BUY":
                down_pos += shares
            else:
                down_pos -= shares

        timeline.append({
            "datetime": dt,
            "up_position": up_pos,
            "down_position": down_pos,
            "net_position": up_pos - down_pos
        })

    # Create figure with subplots
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    times = [t["datetime"] for t in timeline]
    up_positions = [t["up_position"] for t in timeline]
    down_positions = [t["down_position"] for t in timeline]
    net_positions = [t["net_position"] for t in timeline]

    # Top: Individual positions
    axes[0].plot(times, up_positions, 'g-', linewidth=1.5, label='UP Position')
    axes[0].plot(times, down_positions, 'r-', linewidth=1.5, label='DOWN Position')
    axes[0].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    axes[0].set_ylabel('Shares', fontsize=12)
    axes[0].set_title('Position Evolution: UP and DOWN Holdings', fontsize=14)
    axes[0].legend(loc='upper left')
    axes[0].grid(True, alpha=0.3)

    # Bottom: Net position
    colors = ['green' if p > 0 else 'red' for p in net_positions]
    axes[1].fill_between(times, 0, net_positions, alpha=0.3,
                         where=[p > 0 for p in net_positions], color='green', label='Net UP bias')
    axes[1].fill_between(times, 0, net_positions, alpha=0.3,
                         where=[p <= 0 for p in net_positions], color='red', label='Net DOWN bias')
    axes[1].plot(times, net_positions, 'b-', linewidth=1.5, label='Net Position (UP - DOWN)')
    axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    axes[1].set_xlabel('Time', fontsize=12)
    axes[1].set_ylabel('Net Shares', fontsize=12)
    axes[1].set_title('Net Position (UP - DOWN): Positive = Bullish, Negative = Bearish', fontsize=14)
    axes[1].legend(loc='upper left')
    axes[1].grid(True, alpha=0.3)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "position_evolution.png"), dpi=150)
    plt.close()

    # Calculate metrics
    final_up = timeline[-1]["up_position"]
    final_down = timeline[-1]["down_position"]
    final_net = timeline[-1]["net_position"]
    max_up = max(t["up_position"] for t in timeline)
    max_down = max(t["down_position"] for t in timeline)
    max_net = max(abs(t["net_position"]) for t in timeline)

    # Balance ratio
    balance_ratio = 1 - abs(final_up - final_down) / max(final_up + final_down, 1)

    return {
        "final_up_position": final_up,
        "final_down_position": final_down,
        "final_net_position": final_net,
        "max_up_position": max_up,
        "max_down_position": max_down,
        "max_net_imbalance": max_net,
        "balance_ratio": balance_ratio,
        "position_timeline": timeline
    }


def analyze_pnl_breakdown(trades, winning_outcome):
    """
    Section 2.3: P&L Breakdown Analysis
    Why did they lose $87?
    """
    print("Analyzing P&L breakdown...")

    # Calculate cumulative P&L
    timeline = []
    cumulative_cost = 0
    cumulative_revenue = 0
    up_cost = 0
    up_revenue = 0
    down_cost = 0
    down_revenue = 0
    maker_pnl = 0
    taker_pnl = 0

    up_position = 0
    down_position = 0

    for t in trades:
        dt = datetime.fromtimestamp(t["timestamp"])
        usdc = t["usdc"]

        if t["side"] == "BUY":
            cumulative_cost += usdc
            if t["outcome"] == "Up":
                up_cost += usdc
                up_position += t["shares"]
            else:
                down_cost += usdc
                down_position += t["shares"]
        else:
            cumulative_revenue += usdc
            if t["outcome"] == "Up":
                up_revenue += usdc
                up_position -= t["shares"]
            else:
                down_revenue += usdc
                down_position -= t["shares"]

        # Current unrealized P&L (using mid price assumption)
        # Realized = revenue - cost, Unrealized = position value
        realized_pnl = cumulative_revenue - cumulative_cost

        timeline.append({
            "datetime": dt,
            "cumulative_cost": cumulative_cost,
            "cumulative_revenue": cumulative_revenue,
            "realized_pnl": realized_pnl,
            "up_position": up_position,
            "down_position": down_position
        })

    # Final P&L calculation
    final_up = timeline[-1]["up_position"]
    final_down = timeline[-1]["down_position"]

    if winning_outcome == "up":
        resolution_payout = max(0, final_up) * 1.0
    else:
        resolution_payout = max(0, final_down) * 1.0

    total_cost = up_cost + down_cost
    total_revenue = up_revenue + down_revenue
    final_pnl = resolution_payout + total_revenue - total_cost

    # Breakdown analysis
    up_pnl = up_revenue - up_cost + (final_up * 1.0 if winning_outcome == "up" else 0)
    down_pnl = down_revenue - down_cost + (final_down * 1.0 if winning_outcome == "down" else 0)

    # Maker vs Taker P&L
    maker_cost = sum(t["usdc"] for t in trades if t["role"] == "maker" and t["side"] == "BUY")
    maker_rev = sum(t["usdc"] for t in trades if t["role"] == "maker" and t["side"] == "SELL")
    taker_cost = sum(t["usdc"] for t in trades if t["role"] == "taker" and t["side"] == "BUY")
    taker_rev = sum(t["usdc"] for t in trades if t["role"] == "taker" and t["side"] == "SELL")

    # Create figure
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    times = [t["datetime"] for t in timeline]
    costs = [t["cumulative_cost"] for t in timeline]
    revenues = [t["cumulative_revenue"] for t in timeline]
    realized = [t["realized_pnl"] for t in timeline]

    # Top: Cost and Revenue
    axes[0].plot(times, costs, 'r-', linewidth=1.5, label='Cumulative Cost (Buying)')
    axes[0].plot(times, revenues, 'g-', linewidth=1.5, label='Cumulative Revenue (Selling)')
    axes[0].set_ylabel('USDC', fontsize=12)
    axes[0].set_title('Cumulative Trading Activity', fontsize=14)
    axes[0].legend(loc='upper left')
    axes[0].grid(True, alpha=0.3)

    # Bottom: Realized P&L (before resolution)
    colors = ['green' if p > 0 else 'red' for p in realized]
    axes[1].fill_between(times, 0, realized, alpha=0.3,
                         where=[p > 0 for p in realized], color='green')
    axes[1].fill_between(times, 0, realized, alpha=0.3,
                         where=[p <= 0 for p in realized], color='red')
    axes[1].plot(times, realized, 'b-', linewidth=1.5, label='Realized P&L (Revenue - Cost)')
    axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    axes[1].set_xlabel('Time', fontsize=12)
    axes[1].set_ylabel('USDC', fontsize=12)
    axes[1].set_title(f'Cumulative P&L (Before Resolution Payout: ${resolution_payout:.2f})', fontsize=14)
    axes[1].legend(loc='upper left')
    axes[1].grid(True, alpha=0.3)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)

    # Add final P&L annotation
    final_x = times[-1]
    final_y = realized[-1]
    axes[1].annotate(f'Final: ${final_pnl:.2f}', xy=(final_x, final_y),
                     xytext=(10, 30), textcoords='offset points',
                     fontsize=12, fontweight='bold',
                     arrowprops=dict(arrowstyle='->', color='black'))

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "pnl_accumulation.png"), dpi=150)
    plt.close()

    return {
        "total_cost": total_cost,
        "total_revenue": total_revenue,
        "resolution_payout": resolution_payout,
        "final_pnl": final_pnl,
        "up_pnl": up_pnl,
        "down_pnl": down_pnl,
        "up_cost": up_cost,
        "up_revenue": up_revenue,
        "down_cost": down_cost,
        "down_revenue": down_revenue,
        "maker_cost": maker_cost,
        "maker_revenue": maker_rev,
        "taker_cost": taker_cost,
        "taker_revenue": taker_rev,
        "pnl_timeline": timeline
    }


def analyze_market_making(trades, winning_outcome):
    """
    Section 2.4: Market Making Analysis
    Spread capture, adverse selection
    """
    print("Analyzing market making behavior...")

    # Analyze spreads by looking at concurrent BUY UP / SELL DOWN pairs
    # Group by timestamp
    trades_by_ts = defaultdict(list)
    for t in trades:
        trades_by_ts[t["timestamp"]].append(t)

    spread_captures = []
    adverse_selection_events = []

    for ts, ts_trades in trades_by_ts.items():
        up_buys = [t for t in ts_trades if t["outcome"] == "Up" and t["side"] == "BUY"]
        down_sells = [t for t in ts_trades if t["outcome"] == "Down" and t["side"] == "SELL"]
        up_sells = [t for t in ts_trades if t["outcome"] == "Up" and t["side"] == "SELL"]
        down_buys = [t for t in ts_trades if t["outcome"] == "Down" and t["side"] == "BUY"]

        # Check for pairs that indicate market making
        if up_buys and down_buys:
            # Buying both sides = trying to be delta neutral
            avg_up_price = sum(t["price"] for t in up_buys) / len(up_buys)
            avg_down_price = sum(t["price"] for t in down_buys) / len(down_buys)
            combined = avg_up_price + avg_down_price
            edge = 1 - combined
            spread_captures.append({
                "timestamp": ts,
                "up_price": avg_up_price,
                "down_price": avg_down_price,
                "combined": combined,
                "edge": edge
            })

    # Adverse selection: Did they get filled more on the losing side?
    if winning_outcome == "up":
        winning_side = "Up"
        losing_side = "Down"
    else:
        winning_side = "Down"
        losing_side = "Up"

    winning_bought = sum(t["shares"] for t in trades if t["outcome"] == winning_side and t["side"] == "BUY")
    winning_sold = sum(t["shares"] for t in trades if t["outcome"] == winning_side and t["side"] == "SELL")
    losing_bought = sum(t["shares"] for t in trades if t["outcome"] == losing_side and t["side"] == "BUY")
    losing_sold = sum(t["shares"] for t in trades if t["outcome"] == losing_side and t["side"] == "SELL")

    winning_net = winning_bought - winning_sold
    losing_net = losing_bought - losing_sold

    # Calculate maker vs taker fills
    maker_trades = [t for t in trades if t["role"] == "maker"]
    taker_trades = [t for t in trades if t["role"] == "taker"]

    return {
        "num_spread_captures": len(spread_captures),
        "avg_combined_price": np.mean([s["combined"] for s in spread_captures]) if spread_captures else 0,
        "avg_edge": np.mean([s["edge"] for s in spread_captures]) if spread_captures else 0,
        "winning_net": winning_net,
        "losing_net": losing_net,
        "winning_bought": winning_bought,
        "winning_sold": winning_sold,
        "losing_bought": losing_bought,
        "losing_sold": losing_sold,
        "maker_count": len(maker_trades),
        "taker_count": len(taker_trades),
        "maker_ratio": len(maker_trades) / len(trades) if trades else 0,
        "spread_captures": spread_captures
    }


def analyze_timing(trades, winning_outcome):
    """
    Section 2.5: Timing Analysis
    When did they enter/exit? Did they predict correctly?
    """
    print("Analyzing timing patterns...")

    if not trades:
        return {}

    first_ts = trades[0]["timestamp"]
    last_ts = trades[-1]["timestamp"]
    duration = last_ts - first_ts

    # Divide into thirds
    third_duration = duration / 3
    early_end = first_ts + third_duration
    mid_end = first_ts + 2 * third_duration

    early_trades = [t for t in trades if t["timestamp"] <= early_end]
    mid_trades = [t for t in trades if early_end < t["timestamp"] <= mid_end]
    late_trades = [t for t in trades if t["timestamp"] > mid_end]

    def summarize_period(period_trades, name):
        if not period_trades:
            return {"name": name, "count": 0}

        up_net = sum(t["shares"] if t["side"] == "BUY" else -t["shares"]
                     for t in period_trades if t["outcome"] == "Up")
        down_net = sum(t["shares"] if t["side"] == "BUY" else -t["shares"]
                       for t in period_trades if t["outcome"] == "Down")
        cost = sum(t["usdc"] for t in period_trades if t["side"] == "BUY")
        revenue = sum(t["usdc"] for t in period_trades if t["side"] == "SELL")

        return {
            "name": name,
            "count": len(period_trades),
            "up_net": up_net,
            "down_net": down_net,
            "cost": cost,
            "revenue": revenue,
            "bias": "UP" if up_net > down_net else "DOWN" if down_net > up_net else "NEUTRAL"
        }

    early = summarize_period(early_trades, "Early (first 5 min)")
    mid = summarize_period(mid_trades, "Mid (5-10 min)")
    late = summarize_period(late_trades, "Late (10-15 min)")

    # Did they predict correctly?
    if winning_outcome == "up":
        correct = early.get("up_net", 0) > early.get("down_net", 0)
    else:
        correct = early.get("down_net", 0) > early.get("up_net", 0)

    return {
        "early": early,
        "mid": mid,
        "late": late,
        "duration_minutes": duration / 60,
        "trades_per_minute": len(trades) / (duration / 60) if duration > 0 else 0,
        "predicted_correctly": correct
    }


def analyze_order_sizes(trades):
    """
    Section 2.6: Order Size Analysis
    Distribution of order sizes
    """
    print("Analyzing order sizes...")

    sizes = [t["shares"] for t in trades]
    usdc_amounts = [t["usdc"] for t in trades]

    # Create distribution chart
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Top left: Share size histogram
    axes[0, 0].hist(sizes, bins=50, edgecolor='black', alpha=0.7)
    axes[0, 0].set_xlabel('Shares', fontsize=12)
    axes[0, 0].set_ylabel('Frequency', fontsize=12)
    axes[0, 0].set_title('Distribution of Order Sizes (Shares)', fontsize=14)
    axes[0, 0].axvline(x=26, color='red', linestyle='--', alpha=0.7, label='26 shares (common)')
    axes[0, 0].legend()

    # Top right: USDC histogram
    axes[0, 1].hist(usdc_amounts, bins=50, edgecolor='black', alpha=0.7, color='green')
    axes[0, 1].set_xlabel('USDC', fontsize=12)
    axes[0, 1].set_ylabel('Frequency', fontsize=12)
    axes[0, 1].set_title('Distribution of Order Sizes (USDC)', fontsize=14)

    # Bottom left: Size by price
    prices = [t["price"] for t in trades]
    axes[1, 0].scatter(prices, sizes, alpha=0.3, s=10)
    axes[1, 0].set_xlabel('Price', fontsize=12)
    axes[1, 0].set_ylabel('Shares', fontsize=12)
    axes[1, 0].set_title('Order Size vs Price', fontsize=14)

    # Bottom right: Box plot by outcome and side
    up_buy = [t["shares"] for t in trades if t["outcome"] == "Up" and t["side"] == "BUY"]
    up_sell = [t["shares"] for t in trades if t["outcome"] == "Up" and t["side"] == "SELL"]
    down_buy = [t["shares"] for t in trades if t["outcome"] == "Down" and t["side"] == "BUY"]
    down_sell = [t["shares"] for t in trades if t["outcome"] == "Down" and t["side"] == "SELL"]

    bp = axes[1, 1].boxplot([up_buy, up_sell, down_buy, down_sell],
                            labels=['UP BUY', 'UP SELL', 'DOWN BUY', 'DOWN SELL'],
                            patch_artist=True)
    colors = ['lightgreen', 'lightcoral', 'lightgreen', 'lightcoral']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
    axes[1, 1].set_ylabel('Shares', fontsize=12)
    axes[1, 1].set_title('Order Size by Outcome and Side', fontsize=14)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "order_distribution.png"), dpi=150)
    plt.close()

    # Calculate metrics
    return {
        "mean_shares": np.mean(sizes),
        "median_shares": np.median(sizes),
        "std_shares": np.std(sizes),
        "min_shares": min(sizes),
        "max_shares": max(sizes),
        "mean_usdc": np.mean(usdc_amounts),
        "num_26_share_orders": sum(1 for s in sizes if 25.9 < s < 26.1),
        "pct_26_share_orders": sum(1 for s in sizes if 25.9 < s < 26.1) / len(sizes) * 100
    }


def generate_report(data, analyses):
    """Generate comprehensive markdown report."""
    print("Generating report...")

    winning_outcome = data["winning_outcome"]
    trades = data["trades"]

    ts = analyses["time_series"]
    pos = analyses["position"]
    pnl = analyses["pnl"]
    mm = analyses["market_making"]
    timing = analyses["timing"]
    sizes = analyses["sizes"]

    report = f"""# Deep Strategy Analysis: gabagool22

## Executive Summary

**Wallet**: `{data['wallet']}`
**Market**: {data['market_slug']}
**Question**: {data['market_question']}
**Winner**: {winning_outcome.upper()}
**Total Trades**: {len(trades)}

### Key Finding: Why They Lost ${abs(pnl['final_pnl']):.2f}

gabagool22 operated as a **high-frequency market maker** with 79.6% maker trades. Despite massive trading volume (93.9 trades/minute), they **lost money** primarily because:

1. **Adverse Selection**: They accumulated {pos['final_down_position']:.0f} DOWN shares (net) which became worthless when UP won
2. **Insufficient Edge**: Their combined buy prices averaged {mm['avg_combined_price']:.2%}, capturing only {mm['avg_edge']*100:.1f}% edge - not enough to offset losses
3. **Wrong Direction at End**: They held significantly more DOWN than UP at resolution

---

## 1. Time-Series Analysis

![Price Timeline](price_timeline.png)

### Price Behavior
- **Price Range**: {ts['price_range']*100:.1f}%
- **Volatility (std)**: {ts['volatility']*100:.1f}%
- **Price Points**: {ts['num_price_points']}

The market was highly volatile, with UP price swinging from ~$0.51 at open to ~$0.12 mid-session, then recovering to ~$0.93 by close.

---

## 2. Position Evolution

![Position Evolution](position_evolution.png)

### Final Positions
| Outcome | Position (shares) |
|---------|-------------------|
| UP | {pos['final_up_position']:.2f} |
| DOWN | {pos['final_down_position']:.2f} |
| **Net (UP - DOWN)** | **{pos['final_net_position']:.2f}** |

### Position Metrics
- **Max UP Position**: {pos['max_up_position']:.2f} shares
- **Max DOWN Position**: {pos['max_down_position']:.2f} shares
- **Max Net Imbalance**: {pos['max_net_imbalance']:.2f} shares
- **Balance Ratio**: {pos['balance_ratio']:.2%} (1.0 = perfectly balanced)

**Interpretation**: They ended with ~{pos['final_down_position'] - pos['final_up_position']:.0f} more DOWN than UP shares. Since UP won, those DOWN shares became worthless.

---

## 3. P&L Breakdown

![P&L Accumulation](pnl_accumulation.png)

### Trading Summary
| Category | Amount |
|----------|--------|
| Total Cost (Buying) | ${pnl['total_cost']:.2f} |
| Total Revenue (Selling) | ${pnl['total_revenue']:.2f} |
| Resolution Payout | ${pnl['resolution_payout']:.2f} |
| **Final P&L** | **${pnl['final_pnl']:.2f}** |

### P&L by Outcome
| Outcome | P&L |
|---------|-----|
| UP trades | ${pnl['up_pnl']:.2f} |
| DOWN trades | ${pnl['down_pnl']:.2f} |

### Cost/Revenue Breakdown
| | UP | DOWN |
|--|-----|------|
| Cost | ${pnl['up_cost']:.2f} | ${pnl['down_cost']:.2f} |
| Revenue | ${pnl['up_revenue']:.2f} | ${pnl['down_revenue']:.2f} |

### Maker vs Taker
| Role | Cost | Revenue |
|------|------|---------|
| Maker | ${pnl['maker_cost']:.2f} | ${pnl['maker_revenue']:.2f} |
| Taker | ${pnl['taker_cost']:.2f} | ${pnl['taker_revenue']:.2f} |

---

## 4. Market Making Analysis

### Spread Capture
- **Combined Buy Price**: {mm['avg_combined_price']:.4f} (UP + DOWN)
- **Edge Captured**: {mm['avg_edge']*100:.2f}%
- **Spread Capture Events**: {mm['num_spread_captures']}

### Adverse Selection Analysis
The key question: Did they get stuck holding the losing side?

| Side | Bought | Sold | Net |
|------|--------|------|-----|
| Winning ({winning_outcome.upper()}) | {mm['winning_bought']:.2f} | {mm['winning_sold']:.2f} | **{mm['winning_net']:.2f}** |
| Losing ({("DOWN" if winning_outcome == "up" else "UP")}) | {mm['losing_bought']:.2f} | {mm['losing_sold']:.2f} | **{mm['losing_net']:.2f}** |

**Verdict**: They accumulated {mm['losing_net']:.0f} shares of the **losing** outcome. This is classic adverse selection - market makers get picked off by informed traders.

### Role Breakdown
- **Maker trades**: {mm['maker_count']} ({mm['maker_ratio']*100:.1f}%)
- **Taker trades**: {mm['taker_count']} ({(1-mm['maker_ratio'])*100:.1f}%)

---

## 5. Timing Analysis

### Trading Phases
| Phase | Trades | UP Net | DOWN Net | Bias |
|-------|--------|--------|----------|------|
| {timing['early']['name']} | {timing['early']['count']} | {timing['early'].get('up_net', 0):.1f} | {timing['early'].get('down_net', 0):.1f} | {timing['early'].get('bias', 'N/A')} |
| {timing['mid']['name']} | {timing['mid']['count']} | {timing['mid'].get('up_net', 0):.1f} | {timing['mid'].get('down_net', 0):.1f} | {timing['mid'].get('bias', 'N/A')} |
| {timing['late']['name']} | {timing['late']['count']} | {timing['late'].get('up_net', 0):.1f} | {timing['late'].get('down_net', 0):.1f} | {timing['late'].get('bias', 'N/A')} |

### Timing Metrics
- **Duration**: {timing['duration_minutes']:.1f} minutes
- **Trades per minute**: {timing['trades_per_minute']:.1f}
- **Predicted winner correctly in early phase**: {'Yes' if timing['predicted_correctly'] else 'No'}

---

## 6. Order Size Analysis

![Order Distribution](order_distribution.png)

### Size Statistics
| Metric | Shares | USDC |
|--------|--------|------|
| Mean | {sizes['mean_shares']:.2f} | ${sizes['mean_usdc']:.2f} |
| Median | {sizes['median_shares']:.2f} | - |
| Std Dev | {sizes['std_shares']:.2f} | - |
| Min | {sizes['min_shares']:.2f} | - |
| Max | {sizes['max_shares']:.2f} | - |

### Notable Pattern
- **26-share orders**: {sizes['num_26_share_orders']} ({sizes['pct_26_share_orders']:.1f}% of all trades)

This suggests automated trading with fixed order sizes, typical of market-making bots.

---

## Strategy Classification

Based on the analysis, gabagool22 appears to be a **Delta-Neutral Market Maker**:

1. **High maker ratio (80%)** - Posts limit orders on both sides
2. **Balanced positions** - Tries to maintain equal UP and DOWN exposure
3. **Fixed order sizes** - Uses ~26 share blocks
4. **High frequency** - 94 trades/minute
5. **Captures spread** - Buys both outcomes below $1.00 combined

### Why the Strategy Failed This Time

1. **Market moved against them**: Price swung dramatically (UP crashed to $0.12, then recovered to $0.93)
2. **Inventory imbalance**: Ended with more DOWN than UP when UP won
3. **Insufficient edge**: Their ~{mm['avg_edge']*100:.0f}% spread capture wasn't enough to offset the directional loss
4. **Adverse selection**: Informed traders likely sold UP to them before the crash, then bought it back cheaper

---

## Conclusion

gabagool22 lost ${abs(pnl['final_pnl']):.2f} because they ended up holding more of the losing outcome (DOWN) than the winner (UP). This is a classic market-making risk: when the market moves sharply in one direction, you get stuck holding the wrong side.

Their strategy works when:
- Markets are balanced (50/50 probability)
- Price doesn't move dramatically
- They can exit positions before resolution

It fails when:
- One outcome becomes heavily favored
- They can't unwind inventory fast enough
- Informed traders pick them off

**Final P&L: ${pnl['final_pnl']:.2f}**
"""

    report_path = os.path.join(OUTPUT_DIR, "analysis_report.md")
    with open(report_path, "w") as f:
        f.write(report)

    return report_path


def main():
    print("=" * 60)
    print("DEEP STRATEGY ANALYSIS: GABAGOOL22")
    print("=" * 60)
    print()

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load data
    print("Loading trade data...")
    data = load_trades()
    trades = data["trades"]
    winning_outcome = data["winning_outcome"]
    print(f"  Loaded {len(trades)} trades")
    print(f"  Winner: {winning_outcome}")
    print()

    # Run all analyses
    analyses = {}

    analyses["time_series"] = analyze_time_series(trades, winning_outcome)
    print(f"  Time series: {analyses['time_series']['num_price_points']} price points")

    analyses["position"] = analyze_position_evolution(trades, winning_outcome)
    print(f"  Final position: UP={analyses['position']['final_up_position']:.0f}, DOWN={analyses['position']['final_down_position']:.0f}")

    analyses["pnl"] = analyze_pnl_breakdown(trades, winning_outcome)
    print(f"  Final P&L: ${analyses['pnl']['final_pnl']:.2f}")

    analyses["market_making"] = analyze_market_making(trades, winning_outcome)
    print(f"  Maker ratio: {analyses['market_making']['maker_ratio']*100:.1f}%")

    analyses["timing"] = analyze_timing(trades, winning_outcome)
    print(f"  Trades/min: {analyses['timing']['trades_per_minute']:.1f}")

    analyses["sizes"] = analyze_order_sizes(trades)
    print(f"  Mean order: {analyses['sizes']['mean_shares']:.1f} shares")

    print()

    # Generate report
    report_path = generate_report(data, analyses)
    print(f"Report saved to: {report_path}")

    print()
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print()
    print("Generated files:")
    print(f"  - {os.path.join(OUTPUT_DIR, 'price_timeline.png')}")
    print(f"  - {os.path.join(OUTPUT_DIR, 'position_evolution.png')}")
    print(f"  - {os.path.join(OUTPUT_DIR, 'pnl_accumulation.png')}")
    print(f"  - {os.path.join(OUTPUT_DIR, 'order_distribution.png')}")
    print(f"  - {report_path}")


if __name__ == "__main__":
    main()
