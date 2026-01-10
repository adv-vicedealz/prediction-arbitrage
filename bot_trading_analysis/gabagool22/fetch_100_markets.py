"""
Fetch and analyze 100 most recent markets for gabagool22.
Skips markets we've already analyzed.

Wallet: 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d
"""

import sys
import os
import json
import requests
import time
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bot_identifier.market_fetcher import (
    fetch_market_metadata,
    fetch_and_parse_market_trades
)

# Configuration
TARGET_WALLET = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# APIs
GAMMA_API = "https://gamma-api.polymarket.com"


def load_existing_results():
    """Load previously analyzed markets."""
    results_file = os.path.join(DATA_DIR, "all_market_results.json")
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            results = json.load(f)
            return {r["slug"]: r for r in results}
    return {}


def generate_updown_slugs(hours_back=72):
    """
    Generate updown market slugs for the last N hours.
    Markets run every 15 minutes, so 4 per hour.

    Slug format: btc-updown-15m-TIMESTAMP or eth-updown-15m-TIMESTAMP
    The timestamp is the END time of the 15-minute window.
    """
    print(f"\nGenerating updown market slugs for last {hours_back} hours...")

    now = int(time.time())
    # Round down to nearest 15 minutes (900 seconds)
    current_slot = (now // 900) * 900

    slugs = []
    assets = ["btc", "eth"]

    # Generate slots going backwards
    for i in range(hours_back * 4):  # 4 slots per hour
        ts = current_slot - (i * 900)
        for asset in assets:
            slug = f"{asset}-updown-15m-{ts}"
            slugs.append(slug)

    print(f"  Generated {len(slugs)} potential slugs")
    return slugs


def verify_market_exists(slug):
    """Check if a market exists and is resolved."""
    try:
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"slug": slug},
            timeout=10
        )
        if resp.status_code != 200:
            return False

        markets = resp.json()
        if not markets:
            return False

        market = markets[0] if isinstance(markets, list) else markets
        return market.get("closed", False)

    except:
        return False


def analyze_market(slug, existing_results):
    """Analyze a single market and return results."""
    # Check if already analyzed
    if slug in existing_results:
        return existing_results[slug], "cached"

    try:
        # Fetch market metadata
        market = fetch_market_metadata(slug)
        if not market:
            return None, "no_metadata"

        if not market.winning_outcome:
            return None, "not_resolved"

        # Fetch all trades
        all_trades = fetch_and_parse_market_trades(market)

        # Filter for target wallet
        wallet_trades = [t for t in all_trades if t.wallet == TARGET_WALLET.lower()]

        if not wallet_trades:
            return None, "no_trades"

        # Sort by timestamp
        wallet_trades.sort(key=lambda t: (t.timestamp, t.id))

        # Calculate metrics
        up_bought = sum(t.shares for t in wallet_trades if t.outcome == "Up" and t.side == "BUY")
        up_sold = sum(t.shares for t in wallet_trades if t.outcome == "Up" and t.side == "SELL")
        down_bought = sum(t.shares for t in wallet_trades if t.outcome == "Down" and t.side == "BUY")
        down_sold = sum(t.shares for t in wallet_trades if t.outcome == "Down" and t.side == "SELL")

        up_net = up_bought - up_sold
        down_net = down_bought - down_sold

        up_cost = sum(t.usdc for t in wallet_trades if t.outcome == "Up" and t.side == "BUY")
        up_rev = sum(t.usdc for t in wallet_trades if t.outcome == "Up" and t.side == "SELL")
        down_cost = sum(t.usdc for t in wallet_trades if t.outcome == "Down" and t.side == "BUY")
        down_rev = sum(t.usdc for t in wallet_trades if t.outcome == "Down" and t.side == "SELL")

        # P&L calculation
        winning_outcome = market.winning_outcome.lower()
        if winning_outcome == "up":
            payout = max(0, up_net) * 1.0
        else:
            payout = max(0, down_net) * 1.0

        total_cost = up_cost + down_cost
        total_rev = up_rev + down_rev
        pnl = payout + total_rev - total_cost

        # Maker ratio
        maker_count = sum(1 for t in wallet_trades if t.role == "maker")
        maker_ratio = maker_count / len(wallet_trades) if wallet_trades else 0

        # Duration
        first_ts = wallet_trades[0].timestamp
        last_ts = wallet_trades[-1].timestamp
        duration_min = (last_ts - first_ts) / 60
        trades_per_min = len(wallet_trades) / duration_min if duration_min > 0 else 0

        # Net bias
        net_bias = "UP" if up_net > down_net else "DOWN" if down_net > up_net else "NEUTRAL"
        correct_bias = (net_bias == "UP" and winning_outcome == "up") or \
                       (net_bias == "DOWN" and winning_outcome == "down")

        result = {
            "slug": slug,
            "question": market.question,
            "winner": winning_outcome,
            "trades": len(wallet_trades),
            "up_net": up_net,
            "down_net": down_net,
            "pnl": pnl,
            "maker_ratio": maker_ratio,
            "duration_min": duration_min,
            "trades_per_min": trades_per_min,
            "net_bias": net_bias,
            "correct_bias": correct_bias,
            "total_volume": total_cost + total_rev
        }

        return result, "new"

    except Exception as e:
        return None, f"error: {e}"


def main():
    print("=" * 70)
    print("FETCHING 100 MOST RECENT MARKETS FOR GABAGOOL22")
    print("=" * 70)
    print(f"Wallet: {TARGET_WALLET}")
    print()

    # Ensure directories exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load existing results
    existing_results = load_existing_results()
    print(f"Already analyzed: {len(existing_results)} markets")

    # Generate potential slugs for last 72 hours (covers ~100 markets per asset)
    generated_slugs = generate_updown_slugs(hours_back=72)

    # Combine with existing analyzed slugs
    all_slugs = set(generated_slugs)
    for slug in existing_results.keys():
        all_slugs.add(slug)

    # Sort by timestamp (newest first)
    def extract_timestamp(slug):
        parts = slug.split("-")
        for part in parts:
            if part.isdigit() and len(part) >= 10:
                return int(part)
        return 0

    sorted_slugs = sorted(all_slugs, key=extract_timestamp, reverse=True)

    # Take top 100 (by timestamp - most recent first)
    target_slugs = sorted_slugs[:100]

    cached_count = sum(1 for s in target_slugs if s in existing_results)
    print(f"\nTargeting {len(target_slugs)} most recent markets")
    print(f"  - Already cached: {cached_count}")
    print(f"  - Need to check: {len(target_slugs) - cached_count}")
    print()

    # Analyze each market
    all_results = []
    stats = {"cached": 0, "new": 0, "no_trades": 0, "error": 0}

    for i, slug in enumerate(target_slugs, 1):
        result, status = analyze_market(slug, existing_results)

        if status == "cached":
            all_results.append(result)
            stats["cached"] += 1
            # Don't print cached ones to reduce noise
        elif status == "new":
            all_results.append(result)
            stats["new"] += 1
            pnl_str = f"${result['pnl']:.2f}"
            win_loss = "WIN" if result['pnl'] > 0 else "LOSS"
            print(f"[{i}/{len(target_slugs)}] {slug}: {result['trades']} trades, {pnl_str} ({win_loss})")
        elif status == "no_trades":
            stats["no_trades"] += 1
            # gabagool22 didn't trade in this market, skip silently
        else:
            stats["error"] += 1
            print(f"[{i}/{len(target_slugs)}] {slug}: {status}")

        # Rate limiting for new fetches
        if status == "new":
            time.sleep(0.3)

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Markets with gabagool22 trades: {len(all_results)}")
    print(f"  - From cache: {stats['cached']}")
    print(f"  - Newly fetched: {stats['new']}")
    print(f"Markets without trades: {stats['no_trades']}")
    print(f"Errors: {stats['error']}")

    if all_results:
        # Sort by P&L for display
        all_results.sort(key=lambda x: x["pnl"], reverse=True)

        # Calculate totals
        total_pnl = sum(r["pnl"] for r in all_results)
        total_trades = sum(r["trades"] for r in all_results)
        total_volume = sum(r["total_volume"] for r in all_results)
        wins = sum(1 for r in all_results if r["pnl"] > 0)
        losses = sum(1 for r in all_results if r["pnl"] <= 0)
        avg_maker = sum(r["maker_ratio"] for r in all_results) / len(all_results)

        print()
        print(f"PERFORMANCE METRICS:")
        print(f"  Markets analyzed: {len(all_results)}")
        print(f"  Total trades: {total_trades:,}")
        print(f"  Total volume: ${total_volume:,.2f}")
        print(f"  Win/Loss: {wins}/{losses} ({100*wins/len(all_results):.1f}% win rate)")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        print(f"  Avg P&L per market: ${total_pnl/len(all_results):.2f}")
        print(f"  Avg maker ratio: {100*avg_maker:.1f}%")
        print(f"  Edge: {100*total_pnl/total_volume:.2f}%")

        print()
        print("TOP 5 MARKETS:")
        for r in all_results[:5]:
            print(f"  {r['slug']}: ${r['pnl']:.2f} ({r['trades']} trades)")

        print()
        print("BOTTOM 5 MARKETS:")
        for r in all_results[-5:]:
            print(f"  {r['slug']}: ${r['pnl']:.2f} ({r['trades']} trades)")

        # Save results (sorted by timestamp for consistency)
        all_results.sort(key=lambda x: extract_timestamp(x["slug"]), reverse=True)

        output_file = os.path.join(DATA_DIR, "all_market_results_100.json")
        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=2)
        print()
        print(f"Saved {len(all_results)} results to {output_file}")

        # Also update the main results file with all markets
        combined = {**existing_results}
        for r in all_results:
            combined[r["slug"]] = r

        combined_list = list(combined.values())
        combined_list.sort(key=lambda x: extract_timestamp(x["slug"]), reverse=True)

        main_output = os.path.join(DATA_DIR, "all_market_results.json")
        with open(main_output, "w") as f:
            json.dump(combined_list, f, indent=2)
        print(f"Updated main results file with {len(combined_list)} total markets")


if __name__ == "__main__":
    main()
