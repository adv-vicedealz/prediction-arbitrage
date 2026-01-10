"""
SQLite database operations for trade storage and analysis
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class Database:
    """SQLite database for storing Polymarket trades"""

    def __init__(self, db_path: str = "data/trades.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        """Create database tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Wallets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL,
                name TEXT,
                first_seen TIMESTAMP,
                last_updated TIMESTAMP,
                total_trades INTEGER DEFAULT 0,
                total_volume_usdc REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Markets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS markets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condition_id TEXT UNIQUE,
                question TEXT,
                slug TEXT,
                category TEXT,
                end_date TIMESTAMP,
                outcomes TEXT,
                clob_token_ids TEXT,
                resolution_source TEXT,
                resolved INTEGER DEFAULT 0,
                outcome_prices TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_hash TEXT NOT NULL,
                block_number INTEGER,
                timestamp TIMESTAMP NOT NULL,
                wallet_id INTEGER REFERENCES wallets(id),
                wallet_address TEXT NOT NULL,
                role TEXT NOT NULL,
                market_id INTEGER REFERENCES markets(id),
                condition_id TEXT,
                token_id TEXT NOT NULL,
                outcome TEXT,
                side TEXT NOT NULL,
                shares REAL NOT NULL,
                usdc_amount REAL NOT NULL,
                price REAL,
                contract TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(transaction_hash, wallet_address, token_id, role)
            )
        """)

        # Create indexes for query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet_address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_condition ON trades(condition_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_tx ON trades(transaction_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_condition ON markets(condition_id)")

        conn.commit()
        conn.close()

    def upsert_wallet(self, address: str, name: Optional[str] = None) -> int:
        """Insert or update wallet, return wallet ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        address = address.lower()
        now = datetime.now()

        cursor.execute("""
            INSERT INTO wallets (address, name, first_seen, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                name = COALESCE(excluded.name, wallets.name),
                last_updated = excluded.last_updated
        """, (address, name, now, now))

        cursor.execute("SELECT id FROM wallets WHERE address = ?", (address,))
        wallet_id = cursor.fetchone()['id']

        conn.commit()
        conn.close()

        return wallet_id

    def upsert_market(self, market_data: Dict[str, Any]) -> int:
        """Insert or update market, return market ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now()

        cursor.execute("""
            INSERT INTO markets (
                condition_id, question, slug, category, end_date,
                outcomes, clob_token_ids, resolution_source,
                resolved, outcome_prices, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(condition_id) DO UPDATE SET
                question = excluded.question,
                slug = excluded.slug,
                category = excluded.category,
                end_date = excluded.end_date,
                outcomes = excluded.outcomes,
                clob_token_ids = excluded.clob_token_ids,
                resolution_source = excluded.resolution_source,
                resolved = excluded.resolved,
                outcome_prices = excluded.outcome_prices,
                updated_at = excluded.updated_at
        """, (
            market_data.get('condition_id'),
            market_data.get('question'),
            market_data.get('slug'),
            market_data.get('category'),
            market_data.get('end_date'),
            market_data.get('outcomes'),
            market_data.get('clob_token_ids'),
            market_data.get('resolution_source'),
            market_data.get('resolved', 0),
            market_data.get('outcome_prices'),
            now
        ))

        cursor.execute(
            "SELECT id FROM markets WHERE condition_id = ?",
            (market_data.get('condition_id'),)
        )
        row = cursor.fetchone()
        market_id = row['id'] if row else None

        conn.commit()
        conn.close()

        return market_id

    def insert_trade(self, trade: Dict[str, Any]) -> bool:
        """Insert a single trade, return True if inserted (not duplicate)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO trades (
                    transaction_hash, block_number, timestamp,
                    wallet_id, wallet_address, role,
                    market_id, condition_id, token_id, outcome,
                    side, shares, usdc_amount, price, contract
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade['transaction_hash'],
                trade.get('block_number'),
                trade['timestamp'],
                trade.get('wallet_id'),
                trade['wallet_address'],
                trade['role'],
                trade.get('market_id'),
                trade.get('condition_id'),
                trade['token_id'],
                trade.get('outcome'),
                trade['side'],
                trade['shares'],
                trade['usdc_amount'],
                trade.get('price'),
                trade['contract']
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate trade
            return False
        finally:
            conn.close()

    def insert_trades_batch(self, trades: List[Dict[str, Any]]) -> int:
        """Insert multiple trades, return count of new trades"""
        inserted = 0
        for trade in trades:
            if self.insert_trade(trade):
                inserted += 1
        return inserted

    def update_wallet_stats(self, wallet_address: str):
        """Update wallet statistics from trades"""
        conn = self._get_connection()
        cursor = conn.cursor()

        wallet_address = wallet_address.lower()

        cursor.execute("""
            UPDATE wallets SET
                total_trades = (
                    SELECT COUNT(*) FROM trades WHERE wallet_address = ?
                ),
                total_volume_usdc = (
                    SELECT COALESCE(SUM(usdc_amount), 0) FROM trades WHERE wallet_address = ?
                ),
                last_updated = CURRENT_TIMESTAMP
            WHERE address = ?
        """, (wallet_address, wallet_address, wallet_address))

        conn.commit()
        conn.close()

    def execute(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a query and return results as list of dicts"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_trade_count(self, wallet_address: str) -> int:
        """Get number of trades for a wallet"""
        result = self.execute(
            "SELECT COUNT(*) as count FROM trades WHERE wallet_address = ?",
            (wallet_address.lower(),)
        )
        return result[0]['count'] if result else 0

    def get_latest_trade_timestamp(self, wallet_address: str) -> Optional[datetime]:
        """Get timestamp of most recent trade for a wallet"""
        result = self.execute(
            "SELECT MAX(timestamp) as latest FROM trades WHERE wallet_address = ?",
            (wallet_address.lower(),)
        )
        if result and result[0]['latest']:
            return datetime.fromisoformat(result[0]['latest'])
        return None

    def get_market_by_token(self, token_id: str) -> Optional[Dict]:
        """Get market info by token ID"""
        result = self.execute(
            "SELECT * FROM markets WHERE clob_token_ids LIKE ?",
            (f'%{token_id}%',)
        )
        return result[0] if result else None
