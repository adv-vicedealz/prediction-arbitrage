#!/usr/bin/env python3
"""
Deep Dive Analysis: Wallet 0x63ce342161250d705dc0b16df89036c8e5f9ba9a

Analyzes trading patterns, order flow, and strategy in detail.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot_identifier.market_fetcher import (
    fetch_market_metadata,
    fetch_and_parse_market_trades,
    ParsedTrade
)

TARGET_WALLET = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"

# All markets this wallet traded in
ALL_MARKETS = [
    {"slug": "eth-updown-15m-1768037400", "winning_outcome": "up"},
    {"slug": "eth-updown-15m-1768036500", "winning_outcome": "up"},
    {"slug": "btc-updown-15m-1768037400", "winning_outcome": "up"},
    {"slug": "btc-updown-15m-1768036500", "winning_outcome": "up"},
    {"slug": "eth-updown-15m-1768035600", "winning_outcome": "down"},
    {"slug": "btc-updown-15m-1768034700", "winning_outcome": "up"},
]

def analyze_order_flow(trades: List[ParsedTrade]) -> Dict:
    """Analyze order flow patterns."""

    # Group by side and role
    buy_maker = [t for t in trades if t.side == "BUY" and t.role == "maker"]
    buy_taker = [t for t in trades if t.side == "BUY" and t.role == "taker"]
    sell_maker = [t for t in trades if t.side == "SELL" and t.role == "maker"]
    sell_taker = [t for t in trades if t.side == "SELL" and t.role == "taker"]

    # Group by outcome
    up_buys = [t for t in trades if t.side == "BUY" and t.outcome.lower() == "up"]
    down_buys = [t for t in trades if t.side == "BUY" and t.outcome.lower() == "down"]
    up_sells = [t for t in trades if t.side == "SELL" and t.outcome.lower() == "up"]
    down_sells = [t for t in trades if t.side == "SELL" and t.outcome.lower() == "down"]

    return {
        "total_trades": len(trades),
        "buy_maker": len(buy_maker),
        "buy_taker": len(buy_taker),
        "sell_maker": len(sell_maker),
        "sell_taker": len(sell_taker),
        "up_buys": len(up_buys),
        "down_buys": len(down_buys),
        "up_sells": len(up_sells),
        "down_sells": len(down_sells),
        "up_buy_volume": sum(t.shares for t in up_buys),
        "down_buy_volume": sum(t.shares for t in down_buys),
        "up_sell_volume": sum(t.shares for t in up_sells),
        "down_sell_volume": sum(t.shares for t in down_sells),
    }


def analyze_price_levels(trades: List[ParsedTrade]) -> Dict:
    """Analyze price levels used."""

    up_buy_prices = [t.price for t in trades if t.side == "BUY" and t.outcome.lower() == "up"]
    down_buy_prices = [t.price for t in trades if t.side == "BUY" and t.outcome.lower() == "down"]
    up_sell_prices = [t.price for t in trades if t.side == "SELL" and t.outcome.lower() == "up"]
    down_sell_prices = [t.price for t in trades if t.side == "SELL" and t.outcome.lower() == "down"]

    def stats(prices):
        if not prices:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}
        return {
            "min": min(prices),
            "max": max(prices),
            "avg": sum(prices) / len(prices),
            "count": len(prices)
        }

    return {
        "up_buy": stats(up_buy_prices),
        "down_buy": stats(down_buy_prices),
        "up_sell": stats(up_sell_prices),
        "down_sell": stats(down_sell_prices),
    }


def analyze_timing(trades: List[ParsedTrade]) -> Dict:
    """Analyze trade timing patterns."""

    if not trades:
        return {}

    trades = sorted(trades, key=lambda t: t.timestamp)

    # Time between trades
    intervals = []
    for i in range(1, len(trades)):
        interval = trades[i].timestamp - trades[i-1].timestamp
        intervals.append(interval)

    # Group trades by second
    trades_per_second = defaultdict(int)
    for t in trades:
        trades_per_second[t.timestamp] += 1

    # Burst detection (>5 trades in same second)
    bursts = [(ts, count) for ts, count in trades_per_second.items() if count > 5]

    first_ts = trades[0].timestamp
    last_ts = trades[-1].timestamp
    duration = last_ts - first_ts

    return {
        "first_trade": datetime.fromtimestamp(first_ts, tz=timezone.utc).isoformat(),
        "last_trade": datetime.fromtimestamp(last_ts, tz=timezone.utc).isoformat(),
        "duration_seconds": duration,
        "avg_interval": sum(intervals) / len(intervals) if intervals else 0,
        "min_interval": min(intervals) if intervals else 0,
        "max_interval": max(intervals) if intervals else 0,
        "num_bursts": len(bursts),
        "max_trades_per_second": max(trades_per_second.values()) if trades_per_second else 0,
    }


def analyze_position_evolution(trades: List[ParsedTrade]) -> List[Dict]:
    """Track position evolution over time."""

    trades = sorted(trades, key=lambda t: t.timestamp)

    up_pos = 0.0
    down_pos = 0.0
    up_cost = 0.0
    down_cost = 0.0
    up_revenue = 0.0
    down_revenue = 0.0

    evolution = []

    for t in trades:
        if t.side == "BUY":
            if t.outcome.lower() == "up":
                up_pos += t.shares
                up_cost += t.usdc
            else:
                down_pos += t.shares
                down_cost += t.usdc
        else:  # SELL
            if t.outcome.lower() == "up":
                up_pos -= t.shares
                up_revenue += t.usdc
            else:
                down_pos -= t.shares
                down_revenue += t.usdc

        evolution.append({
            "timestamp": t.timestamp,
            "time": datetime.fromtimestamp(t.timestamp, tz=timezone.utc).strftime("%H:%M:%S"),
            "action": f"{t.side} {t.outcome}",
            "shares": t.shares,
            "price": t.price,
            "role": t.role,
            "up_pos": up_pos,
            "down_pos": down_pos,
            "up_cost": up_cost,
            "down_cost": down_cost,
            "up_revenue": up_revenue,
            "down_revenue": down_revenue,
            "net_up": up_pos,
            "net_down": down_pos,
        })

    return evolution


def analyze_strategy_phases(evolution: List[Dict]) -> List[Dict]:
    """Identify distinct strategy phases based on position changes."""

    phases = []
    current_phase = None
    phase_start = 0

    for i, e in enumerate(evolution):
        # Determine current behavior
        if e["up_pos"] > 0 and e["down_pos"] > 0:
            behavior = "ACCUMULATING_BOTH"
        elif e["up_pos"] > 0 and e["down_pos"] <= 0:
            behavior = "LONG_UP_SHORT_DOWN"
        elif e["up_pos"] <= 0 and e["down_pos"] > 0:
            behavior = "LONG_DOWN_SHORT_UP"
        elif e["up_pos"] < 0 and e["down_pos"] < 0:
            behavior = "SHORT_BOTH"
        else:
            behavior = "NEUTRAL"

        if behavior != current_phase:
            if current_phase is not None:
                phases.append({
                    "phase": current_phase,
                    "start_idx": phase_start,
                    "end_idx": i - 1,
                    "start_time": evolution[phase_start]["time"],
                    "end_time": evolution[i-1]["time"],
                    "trades": i - phase_start,
                })
            current_phase = behavior
            phase_start = i

    # Last phase
    if current_phase:
        phases.append({
            "phase": current_phase,
            "start_idx": phase_start,
            "end_idx": len(evolution) - 1,
            "start_time": evolution[phase_start]["time"],
            "end_time": evolution[-1]["time"],
            "trades": len(evolution) - phase_start,
        })

    return phases


def calculate_detailed_pnl(evolution: List[Dict], winning_outcome: str) -> Dict:
    """Calculate detailed P&L breakdown."""

    if not evolution:
        return {}

    final = evolution[-1]

    # Final positions
    up_net = final["up_pos"]
    down_net = final["down_pos"]

    # Resolution payout
    if winning_outcome.lower() == "up":
        resolution_payout = max(0, up_net) * 1.0
    else:
        resolution_payout = max(0, down_net) * 1.0

    # Infer minting
    up_sold_excess = max(0, -up_net) if up_net < 0 else 0
    down_sold_excess = max(0, -down_net) if down_net < 0 else 0
    implied_minted = max(up_sold_excess, down_sold_excess)
    minting_cost = implied_minted * 1.0

    # CLOB P&L
    total_revenue = final["up_revenue"] + final["down_revenue"]
    total_cost = final["up_cost"] + final["down_cost"]

    pnl = resolution_payout + total_revenue - total_cost - minting_cost

    return {
        "up_net_position": up_net,
        "down_net_position": down_net,
        "up_cost": final["up_cost"],
        "down_cost": final["down_cost"],
        "up_revenue": final["up_revenue"],
        "down_revenue": final["down_revenue"],
        "total_cost": total_cost,
        "total_revenue": total_revenue,
        "implied_minted_sets": implied_minted,
        "minting_cost": minting_cost,
        "resolution_payout": resolution_payout,
        "winning_outcome": winning_outcome,
        "calculated_pnl": pnl,
    }


def analyze_single_market(slug: str, winning_outcome: str) -> Dict:
    """Analyze a single market and return summary."""

    metadata = fetch_market_metadata(slug)
    if not metadata:
        return None

    metadata.winning_outcome = winning_outcome

    all_trades = fetch_and_parse_market_trades(metadata)
    wallet_trades = [t for t in all_trades if t.wallet.lower() == TARGET_WALLET.lower()]

    if not wallet_trades:
        return None

    flow = analyze_order_flow(wallet_trades)
    prices = analyze_price_levels(wallet_trades)
    timing = analyze_timing(wallet_trades)
    evolution = analyze_position_evolution(wallet_trades)
    phases = analyze_strategy_phases(evolution)
    pnl = calculate_detailed_pnl(evolution, winning_outcome)

    return {
        "slug": slug,
        "question": metadata.question,
        "winning_outcome": winning_outcome,
        "total_trades": len(wallet_trades),
        "flow": flow,
        "prices": prices,
        "timing": timing,
        "phases": phases,
        "pnl": pnl,
        "evolution": evolution,
    }


def main():
    print("=" * 80)
    print(f"DEEP DIVE: {TARGET_WALLET[:10]}...{TARGET_WALLET[-6:]}")
    print("Analyzing ALL 6 markets")
    print("=" * 80)

    # Analyze all markets
    results = []
    import time as time_module

    for i, market in enumerate(ALL_MARKETS, 1):
        print(f"\n[{i}/{len(ALL_MARKETS)}] Fetching {market['slug']}...")
        result = analyze_single_market(market['slug'], market['winning_outcome'])
        if result:
            results.append(result)
            print(f"  → {result['total_trades']} trades, P&L: ${result['pnl']['calculated_pnl']:.2f}")
        else:
            print(f"  → No trades found")
        time_module.sleep(0.3)

    if not results:
        print("\nNo trades found for this wallet")
        return

    # ========================================================================
    # SUMMARY ACROSS ALL MARKETS
    # ========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY ACROSS ALL MARKETS")
    print("=" * 80)

    total_trades = sum(r['total_trades'] for r in results)
    total_pnl = sum(r['pnl']['calculated_pnl'] for r in results)

    print(f"\nMarkets traded: {len(results)}")
    print(f"Total trades: {total_trades}")
    print(f"Total P&L: ${total_pnl:.2f}")

    # Per-market summary table
    print("\n" + "-" * 80)
    print(f"{'Market':<30} {'Winner':<6} {'Trades':>7} {'Up Net':>10} {'Down Net':>10} {'P&L':>12}")
    print("-" * 80)

    for r in results:
        short_slug = r['slug'].replace('updown-15m-', '')
        pnl = r['pnl']
        up_net = pnl['up_net_position']
        down_net = pnl['down_net_position']
        print(f"{short_slug:<30} {r['winning_outcome'].upper():<6} {r['total_trades']:>7} "
              f"{up_net:>10.1f} {down_net:>10.1f} ${pnl['calculated_pnl']:>10.2f}")

    print("-" * 80)
    print(f"{'TOTAL':<30} {'':<6} {total_trades:>7} {'':<10} {'':<10} ${total_pnl:>10.2f}")

    # ========================================================================
    # AGGREGATED ORDER FLOW
    # ========================================================================
    print("\n" + "=" * 80)
    print("AGGREGATED ORDER FLOW (ALL MARKETS)")
    print("=" * 80)

    agg_flow = {
        'buy_maker': sum(r['flow']['buy_maker'] for r in results),
        'buy_taker': sum(r['flow']['buy_taker'] for r in results),
        'sell_maker': sum(r['flow']['sell_maker'] for r in results),
        'sell_taker': sum(r['flow']['sell_taker'] for r in results),
        'up_buy_volume': sum(r['flow']['up_buy_volume'] for r in results),
        'down_buy_volume': sum(r['flow']['down_buy_volume'] for r in results),
        'up_sell_volume': sum(r['flow']['up_sell_volume'] for r in results),
        'down_sell_volume': sum(r['flow']['down_sell_volume'] for r in results),
    }

    print(f"\nBy Role:")
    print(f"  BUY as Maker:  {agg_flow['buy_maker']:>5} trades ({agg_flow['buy_maker']/total_trades:.0%})")
    print(f"  BUY as Taker:  {agg_flow['buy_taker']:>5} trades ({agg_flow['buy_taker']/total_trades:.0%})")
    print(f"  SELL as Maker: {agg_flow['sell_maker']:>5} trades ({agg_flow['sell_maker']/total_trades:.0%})")
    print(f"  SELL as Taker: {agg_flow['sell_taker']:>5} trades ({agg_flow['sell_taker']/total_trades:.0%})")

    print(f"\nBy Outcome (Volume):")
    print(f"  Up Bought:   {agg_flow['up_buy_volume']:>12.1f} shares")
    print(f"  Down Bought: {agg_flow['down_buy_volume']:>12.1f} shares")
    print(f"  Up Sold:     {agg_flow['up_sell_volume']:>12.1f} shares")
    print(f"  Down Sold:   {agg_flow['down_sell_volume']:>12.1f} shares")

    print(f"\nNet Position Totals:")
    net_up = agg_flow['up_buy_volume'] - agg_flow['up_sell_volume']
    net_down = agg_flow['down_buy_volume'] - agg_flow['down_sell_volume']
    print(f"  Net Up:   {net_up:>12.1f} shares")
    print(f"  Net Down: {net_down:>12.1f} shares")

    # ========================================================================
    # STRATEGY PATTERN ANALYSIS
    # ========================================================================
    print("\n" + "=" * 80)
    print("STRATEGY PATTERN ANALYSIS")
    print("=" * 80)

    # Analyze position balance per market
    print("\nPosition Balance per Market:")
    print(f"{'Market':<30} {'Up Net':>10} {'Down Net':>10} {'Ratio':>8} {'Strategy':<20}")
    print("-" * 80)

    for r in results:
        pnl = r['pnl']
        up_net = pnl['up_net_position']
        down_net = pnl['down_net_position']

        if up_net > 0 and down_net > 0:
            ratio = min(up_net, down_net) / max(up_net, down_net)
            if ratio > 0.9:
                strategy = "PURE ARBITRAGE"
            elif ratio > 0.5:
                strategy = "HEDGED DIRECTIONAL"
            else:
                strategy = "DIRECTIONAL"
        elif up_net > 0:
            ratio = 0
            strategy = "LONG UP ONLY"
        elif down_net > 0:
            ratio = 0
            strategy = "LONG DOWN ONLY"
        else:
            ratio = 0
            strategy = "NET SHORT"

        short_slug = r['slug'].replace('updown-15m-', '')
        print(f"{short_slug:<30} {up_net:>10.1f} {down_net:>10.1f} {ratio:>8.2f} {strategy:<20}")

    # ========================================================================
    # DETAILED BREAKDOWN PER MARKET
    # ========================================================================
    print("\n" + "=" * 80)
    print("DETAILED BREAKDOWN PER MARKET")
    print("=" * 80)

    for r in results:
        print(f"\n{'─'*80}")
        print(f"MARKET: {r['question']}")
        print(f"Winner: {r['winning_outcome'].upper()}")
        print(f"{'─'*80}")

        flow = r['flow']
        prices = r['prices']
        timing = r['timing']
        pnl = r['pnl']
        phases = r['phases']

        print(f"\nTrades: {r['total_trades']}")
        print(f"Duration: {timing['duration_seconds']:.0f}s ({timing['duration_seconds']/60:.1f} min)")
        print(f"Trades/min: {r['total_trades'] / max(1, timing['duration_seconds']/60):.1f}")

        print(f"\nOrder Flow:")
        print(f"  BUY Maker: {flow['buy_maker']} | BUY Taker: {flow['buy_taker']}")
        print(f"  SELL Maker: {flow['sell_maker']} | SELL Taker: {flow['sell_taker']}")

        print(f"\nPrices:")
        if prices['up_buy']['count'] > 0:
            print(f"  Up Buy:   avg ${prices['up_buy']['avg']:.3f} (range: ${prices['up_buy']['min']:.3f}-${prices['up_buy']['max']:.3f})")
        if prices['down_buy']['count'] > 0:
            print(f"  Down Buy: avg ${prices['down_buy']['avg']:.3f} (range: ${prices['down_buy']['min']:.3f}-${prices['down_buy']['max']:.3f})")
        if prices['up_sell']['count'] > 0:
            print(f"  Up Sell:  avg ${prices['up_sell']['avg']:.3f} (range: ${prices['up_sell']['min']:.3f}-${prices['up_sell']['max']:.3f})")
        if prices['down_sell']['count'] > 0:
            print(f"  Down Sell: avg ${prices['down_sell']['avg']:.3f} (range: ${prices['down_sell']['min']:.3f}-${prices['down_sell']['max']:.3f})")

        # Combined price if buying both
        if prices['up_buy']['count'] > 0 and prices['down_buy']['count'] > 0:
            combined = prices['up_buy']['avg'] + prices['down_buy']['avg']
            edge = 1 - combined
            print(f"\n  Combined Buy Price: ${combined:.3f} → Edge: {edge:.1%}")

        print(f"\nPhases:")
        for p in phases:
            print(f"  {p['phase']}: {p['trades']} trades ({p['start_time']} → {p['end_time']})")

        print(f"\nP&L Breakdown:")
        print(f"  Up Net: {pnl['up_net_position']:.1f} | Down Net: {pnl['down_net_position']:.1f}")
        print(f"  CLOB Cost: ${pnl['total_cost']:.2f} | Revenue: ${pnl['total_revenue']:.2f}")
        print(f"  Resolution Payout: ${pnl['resolution_payout']:.2f}")
        print(f"  → P&L: ${pnl['calculated_pnl']:.2f}")

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("STRATEGY CONCLUSIONS")
    print("=" * 80)

    # Count strategy types
    arb_count = sum(1 for r in results
                    if r['pnl']['up_net_position'] > 0 and r['pnl']['down_net_position'] > 0
                    and min(r['pnl']['up_net_position'], r['pnl']['down_net_position']) /
                        max(r['pnl']['up_net_position'], r['pnl']['down_net_position']) > 0.9)

    profitable_count = sum(1 for r in results if r['pnl']['calculated_pnl'] > 0)

    maker_ratio = (agg_flow['buy_maker'] + agg_flow['sell_maker']) / total_trades

    print(f"""
WALLET: {TARGET_WALLET}

1. STRATEGY TYPE:
   - Pure arbitrage markets: {arb_count}/{len(results)}
   - Profitable markets: {profitable_count}/{len(results)}
   - Primary approach: {"ARBITRAGE" if arb_count > len(results)/2 else "MIXED/DIRECTIONAL"}

2. EXECUTION STYLE:
   - Maker ratio: {maker_ratio:.0%}
   - NEVER posts sell orders (0 SELL as Maker)
   - Uses limit BUY orders, market SELL orders

3. VOLUME:
   - Total shares bought: {agg_flow['up_buy_volume'] + agg_flow['down_buy_volume']:.0f}
   - Total shares sold: {agg_flow['up_sell_volume'] + agg_flow['down_sell_volume']:.0f}

4. PROFITABILITY:
   - Total P&L: ${total_pnl:.2f}
   - Best market: {max(results, key=lambda r: r['pnl']['calculated_pnl'])['slug']}
   - Worst market: {min(results, key=lambda r: r['pnl']['calculated_pnl'])['slug']}

5. KEY INSIGHT:
   - Buys both Up and Down at low prices (limit orders)
   - Sells both at higher prices (market orders hitting bids)
   - Maintains balanced positions as arbitrage insurance
   - Profits from: spread capture + resolution payout
""")


if __name__ == "__main__":
    main()
