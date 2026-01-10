#!/usr/bin/env python3
"""
Performance Analyzer for Paper Trading Results

Analyzes completed sessions to identify:
1. What's working well
2. What needs improvement
3. Patterns in profitable vs losing trades
4. Optimal parameters

Run with: python3 paper_trading/analyzer.py
"""
import json
import os
from datetime import datetime
from typing import List, Dict
import statistics

DATA_DIR = "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/data"
RESULTS_FILE = "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/all_results.json"


def load_sessions() -> List[Dict]:
    """Load all session results."""
    sessions = []

    # Load from individual files
    if os.path.exists(DATA_DIR):
        for filename in os.listdir(DATA_DIR):
            if filename.startswith("session_") and filename.endswith(".json"):
                filepath = os.path.join(DATA_DIR, filename)
                try:
                    with open(filepath) as f:
                        sessions.append(json.load(f))
                except:
                    pass

    # Also load from aggregate file
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE) as f:
                data = json.load(f)
                for s in data.get("sessions", []):
                    # Avoid duplicates
                    if s.get("market_id") not in [x.get("market_id") for x in sessions]:
                        sessions.append(s)
        except:
            pass

    return sessions


def analyze_performance(sessions: List[Dict]):
    """Analyze overall performance."""
    print("="*70)
    print("PERFORMANCE ANALYSIS")
    print("="*70)

    if not sessions:
        print("\nNo sessions to analyze.")
        return

    resolved = [s for s in sessions if s.get("resolved")]
    unresolved = [s for s in sessions if not s.get("resolved")]

    print(f"\nTotal Sessions: {len(sessions)}")
    print(f"Resolved: {len(resolved)}")
    print(f"Unresolved: {len(unresolved)}")

    if not resolved:
        print("\nNo resolved sessions to analyze.")
        return

    # P&L Analysis
    pnls = [s.get("actual_pnl", 0) for s in resolved]
    total_pnl = sum(pnls)
    avg_pnl = statistics.mean(pnls)
    median_pnl = statistics.median(pnls)

    print(f"\n--- P&L ANALYSIS ---")
    print(f"Total P&L: ${total_pnl:.2f}")
    print(f"Average P&L: ${avg_pnl:.2f}")
    print(f"Median P&L: ${median_pnl:.2f}")
    print(f"Best Session: ${max(pnls):.2f}")
    print(f"Worst Session: ${min(pnls):.2f}")

    if len(pnls) > 1:
        print(f"Std Dev: ${statistics.stdev(pnls):.2f}")

    # Win/Loss
    wins = [s for s in resolved if s.get("actual_pnl", 0) > 0]
    losses = [s for s in resolved if s.get("actual_pnl", 0) <= 0]

    print(f"\n--- WIN/LOSS ---")
    print(f"Wins: {len(wins)} ({100*len(wins)/len(resolved):.1f}%)")
    print(f"Losses: {len(losses)} ({100*len(losses)/len(resolved):.1f}%)")

    if wins:
        avg_win = statistics.mean([s.get("actual_pnl", 0) for s in wins])
        print(f"Average Win: ${avg_win:.2f}")

    if losses:
        avg_loss = statistics.mean([s.get("actual_pnl", 0) for s in losses])
        print(f"Average Loss: ${avg_loss:.2f}")

    # Edge Analysis
    edges = [s.get("edge", 0) for s in resolved if s.get("edge")]
    if edges:
        print(f"\n--- EDGE ANALYSIS ---")
        print(f"Average Edge: {100*statistics.mean(edges):.2f}%")
        print(f"Min Edge: {100*min(edges):.2f}%")
        print(f"Max Edge: {100*max(edges):.2f}%")

    # Inventory Analysis
    imbalances = [s.get("max_imbalance_ratio", 1) for s in resolved]
    if imbalances:
        print(f"\n--- INVENTORY ANALYSIS ---")
        print(f"Average Max Imbalance: {statistics.mean(imbalances):.2f}")
        print(f"Worst Imbalance: {max(imbalances):.2f}")

    # Correlation: Imbalance vs P&L
    print(f"\n--- IMBALANCE VS P&L ---")
    high_imbalance = [s for s in resolved if s.get("max_imbalance_ratio", 1) > 1.5]
    low_imbalance = [s for s in resolved if s.get("max_imbalance_ratio", 1) <= 1.5]

    if high_imbalance:
        avg_pnl_high = statistics.mean([s.get("actual_pnl", 0) for s in high_imbalance])
        print(f"High Imbalance (>1.5) Sessions: {len(high_imbalance)}, Avg P&L: ${avg_pnl_high:.2f}")

    if low_imbalance:
        avg_pnl_low = statistics.mean([s.get("actual_pnl", 0) for s in low_imbalance])
        print(f"Low Imbalance (<=1.5) Sessions: {len(low_imbalance)}, Avg P&L: ${avg_pnl_low:.2f}")


def analyze_patterns(sessions: List[Dict]):
    """Analyze patterns in winning vs losing trades."""
    print("\n" + "="*70)
    print("PATTERN ANALYSIS")
    print("="*70)

    resolved = [s for s in sessions if s.get("resolved")]
    if not resolved:
        return

    wins = [s for s in resolved if s.get("actual_pnl", 0) > 0]
    losses = [s for s in resolved if s.get("actual_pnl", 0) <= 0]

    # Winner distribution
    up_wins = [s for s in resolved if s.get("winner") == "Up"]
    down_wins = [s for s in resolved if s.get("winner") == "Down"]

    print(f"\n--- MARKET OUTCOMES ---")
    print(f"Up Wins: {len(up_wins)} ({100*len(up_wins)/len(resolved):.1f}%)")
    print(f"Down Wins: {len(down_wins)} ({100*len(down_wins)/len(resolved):.1f}%)")

    # Position bias when winning/losing
    print(f"\n--- POSITION BIAS ---")

    if wins:
        up_heavy_wins = [s for s in wins if s.get("unhedged_up", 0) > s.get("unhedged_down", 0)]
        down_heavy_wins = [s for s in wins if s.get("unhedged_down", 0) > s.get("unhedged_up", 0)]
        balanced_wins = [s for s in wins if s.get("unhedged_up", 0) == s.get("unhedged_down", 0)]

        print(f"Winning sessions:")
        print(f"  Up-heavy: {len(up_heavy_wins)}")
        print(f"  Down-heavy: {len(down_heavy_wins)}")
        print(f"  Balanced: {len(balanced_wins)}")

    if losses:
        up_heavy_losses = [s for s in losses if s.get("unhedged_up", 0) > s.get("unhedged_down", 0)]
        down_heavy_losses = [s for s in losses if s.get("unhedged_down", 0) > s.get("unhedged_up", 0)]

        print(f"Losing sessions:")
        print(f"  Up-heavy: {len(up_heavy_losses)}")
        print(f"  Down-heavy: {len(down_heavy_losses)}")

    # Fill analysis
    print(f"\n--- FILL ANALYSIS ---")
    total_fills = [s.get("total_fills", 0) for s in resolved]
    if total_fills:
        print(f"Average Fills per Session: {statistics.mean(total_fills):.0f}")

    rebalances = [s.get("rebalance_count", 0) for s in resolved]
    if rebalances:
        print(f"Average Rebalances per Session: {statistics.mean(rebalances):.1f}")


def identify_improvements(sessions: List[Dict]):
    """Identify potential improvements."""
    print("\n" + "="*70)
    print("IMPROVEMENT OPPORTUNITIES")
    print("="*70)

    resolved = [s for s in sessions if s.get("resolved")]
    if not resolved:
        return

    recommendations = []

    # Check inventory management
    high_imbalance = [s for s in resolved if s.get("max_imbalance_ratio", 1) > 2.0]
    if len(high_imbalance) > len(resolved) * 0.3:
        recommendations.append({
            "issue": "High inventory imbalance in >30% of sessions",
            "recommendation": "Lower max_inventory_ratio from 1.5 to 1.3",
            "expected_impact": "Reduce directional risk, may slightly lower fill rate"
        })

    # Check edge capture
    edges = [s.get("edge", 0) for s in resolved]
    if edges and statistics.mean(edges) < 0.02:
        recommendations.append({
            "issue": "Average edge below 2%",
            "recommendation": "Increase target_edge from 0.03 to 0.04",
            "expected_impact": "Higher profit per set, but fewer fills"
        })

    # Check losses from unhedged positions
    losses = [s for s in resolved if s.get("actual_pnl", 0) < 0]
    if losses:
        unhedged_losses = [s for s in losses if s.get("unhedged_up", 0) > 50 or s.get("unhedged_down", 0) > 50]
        if len(unhedged_losses) > len(losses) * 0.5:
            recommendations.append({
                "issue": "Most losses from unhedged positions",
                "recommendation": "More aggressive rebalancing when imbalanced",
                "expected_impact": "Lower risk but slightly reduced edge"
            })

    # Check fill rate
    total_fills = [s.get("total_fills", 0) for s in resolved]
    total_polls = [s.get("total_polls", 1) for s in resolved]
    fill_rates = [f/p for f, p in zip(total_fills, total_polls) if p > 0]

    if fill_rates and statistics.mean(fill_rates) < 0.3:
        recommendations.append({
            "issue": "Low fill rate (<30%)",
            "recommendation": "Increase fill_probability or bid more aggressively",
            "expected_impact": "More fills, more inventory to manage"
        })

    # Print recommendations
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['issue']}")
            print(f"   Recommendation: {rec['recommendation']}")
            print(f"   Expected Impact: {rec['expected_impact']}")
    else:
        print("\nNo specific improvements identified. Strategy performing well!")

    # General tips
    print("\n--- GENERAL TIPS ---")
    print("1. Run during high-volume periods (US market hours)")
    print("2. Monitor BTC volatility - higher volatility = more fills but more risk")
    print("3. Consider reducing position size as market approaches resolution")
    print("4. Track actual market fills to calibrate simulation accuracy")


def generate_report(sessions: List[Dict]):
    """Generate a comprehensive report."""
    print("\n" + "="*70)
    print("PAPER TRADING REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    analyze_performance(sessions)
    analyze_patterns(sessions)
    identify_improvements(sessions)

    # Save report
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_sessions": len(sessions),
        "resolved_sessions": len([s for s in sessions if s.get("resolved")]),
        "sessions": sessions
    }

    report_file = "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/analysis_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n\nReport saved to: {report_file}")


def main():
    sessions = load_sessions()
    generate_report(sessions)


if __name__ == "__main__":
    main()
