#!/usr/bin/env python3
"""
Polymarket Trade Analyzer
Downloads and analyzes trading history for specified wallets

Usage:
    python main.py --wallet 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d --days 7
    python main.py --wallet 0x6031... --name gabagool22 --analyze-only
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from analyzer.fetcher import TradeFetcher
from analyzer.database import Database
from analyzer import queries


def print_table(rows, headers=None):
    """Simple table printer"""
    if not rows:
        print("  No data")
        return

    # Convert to list of dicts if needed
    if hasattr(rows[0], 'keys'):
        rows = [dict(r) for r in rows]

    if headers is None:
        headers = list(rows[0].keys())

    # Calculate column widths
    widths = {h: len(str(h)) for h in headers}
    for row in rows:
        for h in headers:
            val = row.get(h, '')
            widths[h] = max(widths[h], len(str(val)[:50]))

    # Print header
    header_line = " | ".join(str(h).ljust(widths[h])[:50] for h in headers)
    print(f"  {header_line}")
    print(f"  {'-' * len(header_line)}")

    # Print rows
    for row in rows[:20]:  # Limit to 20 rows
        line = " | ".join(str(row.get(h, '')).ljust(widths[h])[:50] for h in headers)
        print(f"  {line}")

    if len(rows) > 20:
        print(f"  ... and {len(rows) - 20} more rows")


def run_analysis(db: Database, wallet_address: str):
    """Run all analysis queries and print results"""
    wallet_address = wallet_address.lower()

    print(f"\n{'='*60}")
    print("ANALYSIS RESULTS")
    print(f"{'='*60}")

    # Summary stats
    print("\n[Summary Statistics]")
    results = db.execute("""
        SELECT
            COUNT(*) as total_trades,
            SUM(usdc_amount) as total_volume,
            AVG(usdc_amount) as avg_trade_size,
            MIN(timestamp) as first_trade,
            MAX(timestamp) as last_trade
        FROM trades WHERE wallet_address = ?
    """, (wallet_address,))
    if results and results[0]['total_trades']:
        r = results[0]
        print(f"  Total trades: {r['total_trades']:,}")
        print(f"  Total volume: ${r['total_volume']:,.2f}")
        print(f"  Avg trade size: ${r['avg_trade_size']:.2f}")
        print(f"  First trade: {r['first_trade']}")
        print(f"  Last trade: {r['last_trade']}")
    else:
        print("  No trades found")
        return

    # Trade frequency by day
    print("\n[Daily Activity]")
    results = db.execute(queries.TRADE_FREQUENCY, (wallet_address,))
    print_table(results[:10], ['trade_date', 'num_trades', 'daily_volume', 'buys', 'sells'])

    # Contract distribution
    print("\n[Exchange Distribution]")
    results = db.execute(queries.CONTRACT_DISTRIBUTION, (wallet_address,))
    print_table(results, ['contract', 'num_trades', 'total_volume', 'buys', 'sells'])

    # Arbitrage detection
    print("\n[Potential Arbitrage Trades]")
    results = db.execute(queries.ARBITRAGE_DETECTION, (wallet_address,))
    if results:
        for r in results[:5]:
            question = r['question'][:60] if r['question'] else 'Unknown'
            print(f"\n  Market: {question}...")
            print(f"    Outcomes traded: {r['outcomes']}")
            print(f"    Total bought: ${r['total_bought']:.2f}")
            print(f"    Shares: {r['shares_bought']:.0f}")
            print(f"    Duration: {r['duration_minutes']:.1f} minutes")
    else:
        print("  No arbitrage patterns detected")

    # Arbitrage P&L
    print("\n[Arbitrage P&L Analysis]")
    results = db.execute(queries.ARBITRAGE_PNL, (wallet_address,))
    if results:
        total_profit = sum(r['guaranteed_profit'] for r in results if r['guaranteed_profit'] and r['guaranteed_profit'] > 0)
        print(f"  Total guaranteed profit: ${total_profit:.2f}")
        print(f"  Markets with arbitrage: {len(results)}")

        for r in results[:5]:
            if r['guaranteed_profit'] and r['guaranteed_profit'] > 0:
                question = r['question'][:50] if r['question'] else 'Unknown'
                print(f"\n    {question}...")
                print(f"      Positions: {r['positions']}")
                print(f"      Cost: ${r['total_cost']:.2f}")
                print(f"      Guaranteed profit: ${r['guaranteed_profit']:.2f}")
    else:
        print("  No arbitrage positions found")

    # Price distribution
    print("\n[Price Distribution]")
    results = db.execute(queries.PRICE_DISTRIBUTION, (wallet_address,))
    buy_results = [r for r in results if r['side'] == 'BUY']
    print("  BUY trades:")
    for r in buy_results:
        pct = '#' * int(r['num_trades'] / 10)
        print(f"    {r['price_range']}: {r['num_trades']:>4} trades ${r['volume']:>10.2f} {pct}")

    # Recent trades
    print("\n[Recent Trades]")
    results = db.execute(queries.RECENT_TRADES, (wallet_address, 10))
    for r in results:
        question = r['question'][:40] if r['question'] else 'Unknown'
        print(f"  {r['timestamp']} | {r['side']:>4} | {r['outcome']:>6} | "
              f"{r['shares']:>8.2f} @ ${r['price']:.2f} | {question}...")


def main():
    parser = argparse.ArgumentParser(
        description='Polymarket Trade Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch and analyze trades for gabagool22
  python main.py --wallet 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d --name gabagool22

  # Fetch last 30 days
  python main.py --wallet 0x6031... --days 30

  # Only run analysis (no fetching)
  python main.py --wallet 0x6031... --analyze-only

  # Skip API enrichment (faster)
  python main.py --wallet 0x6031... --skip-enrichment
        """
    )

    parser.add_argument(
        '--wallet', '-w',
        default='0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d',
        help='Wallet address to analyze (default: gabagool22)'
    )
    parser.add_argument(
        '--name', '-n',
        default='gabagool22',
        help='Wallet display name'
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=7,
        help='Number of days of history to fetch (default: 7)'
    )
    parser.add_argument(
        '--db',
        default='data/trades.db',
        help='SQLite database path (default: data/trades.db)'
    )
    parser.add_argument(
        '--analyze-only', '-a',
        action='store_true',
        help='Skip fetching, only run analysis on existing data'
    )
    parser.add_argument(
        '--skip-enrichment', '-s',
        action='store_true',
        help='Skip API enrichment (faster but less metadata)'
    )

    args = parser.parse_args()

    # Validate wallet address
    if not args.wallet.startswith('0x') or len(args.wallet) != 42:
        print(f"Error: Invalid wallet address: {args.wallet}")
        sys.exit(1)

    # Initialize
    fetcher = TradeFetcher(db_path=args.db)
    db = Database(args.db)

    # Fetch trades
    if not args.analyze_only:
        result = fetcher.fetch_wallet_trades(
            wallet_address=args.wallet,
            wallet_name=args.name,
            days=args.days,
            skip_enrichment=args.skip_enrichment
        )

        if result['trades_found'] == 0:
            print("\nNo trades found for this wallet in the specified time range.")
            print("Try increasing --days or check the wallet address.")
            sys.exit(0)

    # Run analysis
    run_analysis(db, args.wallet)

    print(f"\n{'='*60}")
    print(f"Database: {args.db}")
    print(f"Run 'sqlite3 {args.db}' to explore data manually")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
