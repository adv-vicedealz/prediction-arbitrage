"""
Main orchestration for fetching and storing Polymarket trades
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .database import Database
from .blockchain import BlockchainClient
from .api import PolymarketAPI
from .config import DEFAULT_DB_PATH


class TradeFetcher:
    """Orchestrates the complete trade fetching pipeline"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db = Database(db_path)
        self.blockchain = BlockchainClient()
        self.api = PolymarketAPI()

    def fetch_wallet_trades(
        self,
        wallet_address: str,
        wallet_name: Optional[str] = None,
        days: int = 7,
        skip_enrichment: bool = False
    ) -> Dict[str, Any]:
        """
        Complete pipeline to fetch, enrich, and store trades

        Args:
            wallet_address: Ethereum wallet address
            wallet_name: Optional display name
            days: Number of days of history to fetch
            skip_enrichment: Skip API enrichment (faster but less data)

        Returns:
            Dict with stats about the fetch operation
        """
        wallet_address = wallet_address.lower()
        start_time = datetime.now()

        print(f"\n{'='*60}")
        print(f"Fetching trades for: {wallet_name or wallet_address[:10]}...")
        print(f"Wallet: {wallet_address}")
        print(f"Time range: Last {days} days")
        print(f"{'='*60}\n")

        # Step 1: Ensure wallet exists in database
        wallet_id = self.db.upsert_wallet(wallet_address, wallet_name)
        print(f"Wallet ID: {wallet_id}")

        # Step 2: Fetch on-chain events
        print(f"\n[1/4] Fetching blockchain events...")
        trades = self.blockchain.fetch_wallet_trades(wallet_address, days)
        print(f"Found {len(trades)} raw trades")

        if not trades:
            return {
                'wallet_address': wallet_address,
                'trades_found': 0,
                'trades_new': 0,
                'markets_found': 0,
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }

        # Step 3: Enrich with market metadata
        if not skip_enrichment:
            print(f"\n[2/4] Enriching with market metadata...")
            trades = self.api.enrich_trades_batch(trades)

            # Store markets in database
            print(f"\n[3/4] Storing markets...")
            markets = self.api.get_cached_markets()
            for market in markets:
                self.db.upsert_market(market)
            print(f"Stored {len(markets)} markets")
        else:
            print(f"\n[2/4] Skipping enrichment (--skip-enrichment)")
            print(f"[3/4] Skipping market storage")
            markets = []

        # Step 4: Store trades
        print(f"\n[4/4] Storing trades...")

        # Add wallet_id and market_id to trades
        for trade in trades:
            trade['wallet_id'] = wallet_id

            # Get market_id if we have condition_id
            if trade.get('condition_id'):
                market_result = self.db.execute(
                    "SELECT id FROM markets WHERE condition_id = ?",
                    (trade['condition_id'],)
                )
                if market_result:
                    trade['market_id'] = market_result[0]['id']

        new_trades = self.db.insert_trades_batch(trades)
        print(f"Stored {new_trades} new trades ({len(trades) - new_trades} duplicates)")

        # Step 5: Update wallet stats
        self.db.update_wallet_stats(wallet_address)

        duration = (datetime.now() - start_time).total_seconds()

        result = {
            'wallet_address': wallet_address,
            'wallet_name': wallet_name,
            'trades_found': len(trades),
            'trades_new': new_trades,
            'trades_duplicate': len(trades) - new_trades,
            'markets_found': len(markets),
            'duration_seconds': duration
        }

        print(f"\n{'='*60}")
        print(f"FETCH COMPLETE")
        print(f"{'='*60}")
        print(f"Trades found: {result['trades_found']}")
        print(f"New trades stored: {result['trades_new']}")
        print(f"Duplicate trades: {result['trades_duplicate']}")
        print(f"Markets enriched: {result['markets_found']}")
        print(f"Duration: {duration:.1f} seconds")

        return result

    def get_summary(self, wallet_address: str) -> Dict[str, Any]:
        """Get summary statistics for a wallet"""
        wallet_address = wallet_address.lower()

        # Basic stats
        trade_count = self.db.get_trade_count(wallet_address)
        latest_trade = self.db.get_latest_trade_timestamp(wallet_address)

        # Volume and P&L
        stats = self.db.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(usdc_amount) as total_volume,
                SUM(CASE WHEN side = 'BUY' THEN usdc_amount ELSE 0 END) as total_bought,
                SUM(CASE WHEN side = 'SELL' THEN usdc_amount ELSE 0 END) as total_sold,
                AVG(usdc_amount) as avg_trade_size,
                MIN(timestamp) as first_trade,
                MAX(timestamp) as last_trade
            FROM trades
            WHERE wallet_address = ?
        """, (wallet_address,))

        if stats:
            return stats[0]
        return {}

    def get_arbitrage_trades(self, wallet_address: str) -> List[Dict]:
        """Find potential arbitrage trades (both sides bought in same market)"""
        return self.db.execute("""
            SELECT
                m.question,
                t.condition_id,
                COUNT(DISTINCT t.outcome) as outcomes_traded,
                GROUP_CONCAT(DISTINCT t.outcome) as outcomes,
                SUM(CASE WHEN t.side = 'BUY' THEN t.usdc_amount ELSE 0 END) as total_bought,
                SUM(CASE WHEN t.side = 'BUY' THEN t.shares ELSE 0 END) as total_shares,
                COUNT(*) as num_trades,
                MIN(t.timestamp) as first_trade,
                MAX(t.timestamp) as last_trade
            FROM trades t
            LEFT JOIN markets m ON t.condition_id = m.condition_id
            WHERE t.wallet_address = ?
            GROUP BY t.condition_id
            HAVING COUNT(DISTINCT t.outcome) > 1
            ORDER BY total_bought DESC
        """, (wallet_address.lower(),))

    def get_daily_activity(self, wallet_address: str) -> List[Dict]:
        """Get daily trading activity"""
        return self.db.execute("""
            SELECT
                date(timestamp) as trade_date,
                COUNT(*) as num_trades,
                SUM(usdc_amount) as daily_volume,
                AVG(usdc_amount) as avg_trade_size,
                SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buys,
                SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sells
            FROM trades
            WHERE wallet_address = ?
            GROUP BY date(timestamp)
            ORDER BY trade_date DESC
        """, (wallet_address.lower(),))

    def get_market_breakdown(self, wallet_address: str, limit: int = 20) -> List[Dict]:
        """Get trading breakdown by market"""
        return self.db.execute("""
            SELECT
                m.question,
                m.category,
                t.outcome,
                SUM(CASE WHEN t.side = 'BUY' THEN t.shares ELSE -t.shares END) as net_shares,
                SUM(CASE WHEN t.side = 'BUY' THEN t.usdc_amount ELSE 0 END) as buy_cost,
                SUM(CASE WHEN t.side = 'SELL' THEN t.usdc_amount ELSE 0 END) as sell_revenue,
                AVG(t.price) as avg_price,
                COUNT(*) as num_trades
            FROM trades t
            LEFT JOIN markets m ON t.condition_id = m.condition_id
            WHERE t.wallet_address = ?
            GROUP BY t.condition_id, t.outcome
            ORDER BY buy_cost DESC
            LIMIT ?
        """, (wallet_address.lower(), limit))
