#!/usr/bin/env python3
"""
Bot Trader Identifier

Analyzes Polymarket BTC/ETH Up/Down markets to identify successful bot traders.

Usage:
    python -m bot_identifier.identify_bots
    python bot_identifier/identify_bots.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import DEFAULT_MARKET_URLS, RATE_LIMIT_DELAY
from .market_fetcher import (
    parse_market_url,
    fetch_market_metadata,
    fetch_and_parse_market_trades,
    MarketMetadata
)
from .trade_aggregator import (
    aggregate_trades,
    calculate_pnl,
    aggregate_across_markets,
    TraderMetrics
)
from .trader_ranker import (
    rank_traders,
    get_likely_bots,
    format_trader_table,
    format_bot_details,
    format_trader_table_with_profiles,
    format_bot_details_with_profiles
)
from .profile_fetcher import fetch_profiles
from .pnl_fetcher import fetch_historical_pnl_batch


def main():
    """Main entry point."""
    print("=" * 70)
    print("BOT TRADER IDENTIFIER")
    print("Analyzing Polymarket BTC/ETH Up/Down markets")
    print("=" * 70)

    # Output directory
    output_dir = Path(__file__).parent.parent / "data" / "bot_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Parse market URLs and fetch metadata
    print("\n[1/6] FETCHING MARKET METADATA")
    print("-" * 40)

    markets = []
    for url in DEFAULT_MARKET_URLS:
        slug = parse_market_url(url)
        print(f"  {slug}...", end=" ")

        metadata = fetch_market_metadata(slug)
        if metadata:
            markets.append(metadata)
            status = "RESOLVED" if metadata.resolved else "ACTIVE"
            winner = f" (Winner: {metadata.winning_outcome})" if metadata.winning_outcome else ""
            print(f"{status}{winner}")
        else:
            print("NOT FOUND")

        time.sleep(RATE_LIMIT_DELAY)

    if not markets:
        print("\nERROR: No markets found. Exiting.")
        return

    print(f"\nFound {len(markets)} markets")

    # Step 2: Fetch all trades for each market
    print("\n[2/6] FETCHING TRADES")
    print("-" * 40)

    all_market_traders = []
    total_trades = 0

    for market in markets:
        print(f"\n  {market.slug}")
        print(f"    Tokens: {list(market.token_ids.keys())}")

        # Fetch trades
        trades = fetch_and_parse_market_trades(market)
        print(f"    Fetched {len(trades)} trade records")

        if not trades:
            continue

        total_trades += len(trades)

        # Aggregate by wallet
        market_traders = aggregate_trades(trades)
        print(f"    Unique traders: {len(market_traders)}")

        # Calculate P&L if market is resolved
        if market.resolved and market.winning_outcome:
            for wallet, metrics in market_traders.items():
                metrics.realized_pnl = calculate_pnl(metrics, market.winning_outcome)

        all_market_traders.append(market_traders)

    print(f"\nTotal trades fetched: {total_trades:,}")

    # Step 3: Aggregate across markets
    print("\n[3/6] AGGREGATING TRADERS")
    print("-" * 40)

    combined_traders = aggregate_across_markets(all_market_traders)
    print(f"Total unique traders: {len(combined_traders):,}")

    # Step 4: Rank and analyze
    print("\n[4/6] RANKING & ANALYSIS")
    print("-" * 40)

    ranked = rank_traders(combined_traders)
    likely_bots = get_likely_bots(ranked)

    print(f"Traders ranked: {len(ranked)}")
    print(f"Likely bots (score >= 70): {len(likely_bots)}")

    # Step 5: Fetch profiles for top traders
    print("\n[5/6] FETCHING PROFILES")
    print("-" * 40)

    top_wallets = [r.wallet for r in ranked[:50]]
    profiles = fetch_profiles(top_wallets, limit=50)
    print(f"Profiles fetched: {len([p for p in profiles.values() if p.username])}/{len(profiles)} with usernames")

    # Step 6: Fetch historical P&L for top traders
    print("\n[6/6] FETCHING HISTORICAL P&L")
    print("-" * 40)

    pnl_wallets = [r.wallet for r in ranked[:50]]
    pnl_data = fetch_historical_pnl_batch(pnl_wallets, include_periods=False, limit=50)

    # Enrich ranked traders with P&L data
    pnl_count = 0
    for r in ranked[:50]:
        pnl = pnl_data.get(r.wallet.lower())
        if pnl:
            r.pnl_all_time = pnl.pnl_all_time
            r.pnl_1d = pnl.pnl_1d
            r.pnl_1w = pnl.pnl_1w
            r.pnl_1m = pnl.pnl_1m
            if pnl.pnl_all_time is not None:
                pnl_count += 1

    print(f"P&L data fetched: {pnl_count}/{len(pnl_wallets)} with all-time P&L")

    # Generate report
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    # Market summary
    print("\nMARKETS ANALYZED")
    print("-" * 40)
    for i, m in enumerate(markets, 1):
        status = "RESOLVED" if m.resolved else "ACTIVE"
        winner = f" - Winner: {m.winning_outcome.upper()}" if m.winning_outcome else ""
        print(f"  {i}. {m.question[:60]}...")
        print(f"     {status}{winner}")

    # Statistics
    print("\nAGGREGATE STATISTICS")
    print("-" * 40)
    total_volume = sum(t.metrics.total_volume_usdc for t in ranked)
    total_pnl = sum(t.metrics.realized_pnl or 0 for t in ranked)
    print(f"  Total trades analyzed: {total_trades:,}")
    print(f"  Total unique traders: {len(ranked):,}")
    print(f"  Total volume traded: ${total_volume:,.0f}")

    # Top traders table with usernames
    print("\nTOP 20 TRADERS BY VOLUME")
    print("-" * 40)
    print(format_trader_table_with_profiles(ranked, profiles, limit=20))

    # Likely bots with usernames
    print("\nLIKELY BOTS (Score >= 70)")
    print("-" * 40)
    print(format_bot_details_with_profiles(ranked, profiles, limit=15))

    # Save results to JSON
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_results.json"

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markets_analyzed": [
            {
                "slug": m.slug,
                "question": m.question,
                "resolved": m.resolved,
                "winning_outcome": m.winning_outcome
            }
            for m in markets
        ],
        "statistics": {
            "total_trades": total_trades,
            "total_traders": len(ranked),
            "total_volume_usdc": total_volume,
            "likely_bots_count": len(likely_bots)
        },
        "traders": [
            {
                "wallet": r.wallet,
                "username": profiles.get(r.wallet.lower()).username if profiles.get(r.wallet.lower()) else None,
                "rank_by_volume": r.rank_by_volume,
                "rank_by_trades": r.rank_by_trades,
                "rank_by_pnl": r.rank_by_pnl,
                "bot_score": r.bot_score,
                "bot_indicators": r.bot_indicators,
                "metrics": {
                    "total_trades": r.metrics.total_trades,
                    "maker_trades": r.metrics.maker_trades,
                    "taker_trades": r.metrics.taker_trades,
                    "maker_ratio": r.metrics.maker_ratio,
                    "total_volume_usdc": r.metrics.total_volume_usdc,
                    "up_bought": r.metrics.up_bought,
                    "up_sold": r.metrics.up_sold,
                    "up_net": r.metrics.up_net,
                    "down_bought": r.metrics.down_bought,
                    "down_sold": r.metrics.down_sold,
                    "down_net": r.metrics.down_net,
                    "realized_pnl": r.metrics.realized_pnl,
                    "position_balance_ratio": r.metrics.position_balance_ratio,
                    "edge": r.metrics.edge,
                    "markets_traded": r.metrics.markets_traded
                },
                "historical_pnl": {
                    "all_time": r.pnl_all_time,
                    "1d": r.pnl_1d,
                    "1w": r.pnl_1w,
                    "1m": r.pnl_1m
                },
                "profile_url": r.profile_url
            }
            for r in ranked[:100]  # Top 100 traders
        ]
    }

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
