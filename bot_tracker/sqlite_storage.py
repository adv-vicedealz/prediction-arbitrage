"""
SQLite storage for trades and market data.
Provides ACID transactions, crash recovery, and efficient queries.
"""

import sqlite3
import json
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path

from .models import TradeEvent, WalletPosition, MarketContext


class SQLiteStorage:
    """Saves tracking data to SQLite database with backup support."""

    def __init__(self, db_dir: str = None):
        """
        Initialize SQLite storage.

        Args:
            db_dir: Directory to save database. Defaults to DATA_DIR env var or bot_tracker/db/
        """
        if db_dir is None:
            db_dir = os.getenv("DATA_DIR", str(Path(__file__).parent / "db"))

        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.db_dir / "tracker.db"
        self.backup_dir = self.db_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = datetime.now()

        # In-memory cache for deduplication
        self.session_trade_ids: set = set()

        # Check for JSON migration
        self._migrate_from_json_if_needed()

        # Connect to database
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrent access and crash recovery
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")

        # Initialize schema
        self._init_schema()

        # Record session start
        self._record_session_start()

        # Create startup backup
        self._create_backup("startup")

        print(f"SQLite storage initialized: {self.db_path}")
        print(f"  Session: {self.session_id}")
        print(f"  Backups: {self.backup_dir}")

    def _init_schema(self):
        """Create database tables if they don't exist."""
        self.conn.executescript("""
            -- Trades table
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                tx_hash TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                wallet TEXT NOT NULL,
                wallet_name TEXT,
                role TEXT,
                side TEXT NOT NULL,
                outcome TEXT NOT NULL,
                shares REAL NOT NULL,
                usdc REAL NOT NULL,
                price REAL NOT NULL,
                fee REAL,
                market_slug TEXT NOT NULL,
                market_question TEXT,
                session_id TEXT,
                recorded_at TEXT NOT NULL
            );

            -- Positions table
            CREATE TABLE IF NOT EXISTS positions (
                wallet TEXT NOT NULL,
                market_slug TEXT NOT NULL,
                wallet_name TEXT,
                up_shares REAL NOT NULL DEFAULT 0,
                down_shares REAL NOT NULL DEFAULT 0,
                up_cost REAL NOT NULL DEFAULT 0,
                down_cost REAL NOT NULL DEFAULT 0,
                complete_sets REAL NOT NULL DEFAULT 0,
                edge REAL NOT NULL DEFAULT 0,
                hedge_ratio REAL NOT NULL DEFAULT 0,
                total_trades INTEGER NOT NULL DEFAULT 0,
                avg_up_price REAL NOT NULL DEFAULT 0,
                avg_down_price REAL NOT NULL DEFAULT 0,
                combined_price REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (wallet, market_slug)
            );

            -- Markets table
            CREATE TABLE IF NOT EXISTS markets (
                slug TEXT PRIMARY KEY,
                question TEXT,
                condition_id TEXT,
                token_ids TEXT,
                outcomes TEXT,
                start_date TEXT,
                end_date TEXT,
                resolved INTEGER DEFAULT 0,
                winning_outcome TEXT,
                updated_at TEXT NOT NULL
            );

            -- Prices table
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                timestamp_iso TEXT,
                market_slug TEXT NOT NULL,
                outcome TEXT NOT NULL,
                price REAL NOT NULL,
                best_bid REAL,
                best_ask REAL,
                session_id TEXT
            );

            -- Sessions table
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                trades_count INTEGER DEFAULT 0
            );

            -- Create indexes for query performance
            CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet);
            CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_slug);
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_prices_market ON prices(market_slug);
            CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON prices(timestamp DESC);
        """)
        self.conn.commit()

    def _migrate_from_json_if_needed(self):
        """Migrate data from JSON files to SQLite if needed."""
        trades_json = self.db_dir / "trades.json"
        positions_json = self.db_dir / "positions.json"
        markets_json = self.db_dir / "markets.json"

        # Check if we need to migrate (JSON exists but DB doesn't)
        if not self.db_path.exists() and trades_json.exists():
            print("Migrating data from JSON to SQLite...")

            # Create temporary connection for migration
            conn = sqlite3.connect(str(self.db_path))

            # Initialize schema first
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    tx_hash TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    wallet TEXT NOT NULL,
                    wallet_name TEXT,
                    role TEXT,
                    side TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    shares REAL NOT NULL,
                    usdc REAL NOT NULL,
                    price REAL NOT NULL,
                    fee REAL,
                    market_slug TEXT NOT NULL,
                    market_question TEXT,
                    session_id TEXT,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS positions (
                    wallet TEXT NOT NULL,
                    market_slug TEXT NOT NULL,
                    wallet_name TEXT,
                    up_shares REAL NOT NULL DEFAULT 0,
                    down_shares REAL NOT NULL DEFAULT 0,
                    up_cost REAL NOT NULL DEFAULT 0,
                    down_cost REAL NOT NULL DEFAULT 0,
                    complete_sets REAL NOT NULL DEFAULT 0,
                    edge REAL NOT NULL DEFAULT 0,
                    hedge_ratio REAL NOT NULL DEFAULT 0,
                    total_trades INTEGER NOT NULL DEFAULT 0,
                    avg_up_price REAL NOT NULL DEFAULT 0,
                    avg_down_price REAL NOT NULL DEFAULT 0,
                    combined_price REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (wallet, market_slug)
                );
                CREATE TABLE IF NOT EXISTS markets (
                    slug TEXT PRIMARY KEY,
                    question TEXT,
                    condition_id TEXT,
                    token_ids TEXT,
                    outcomes TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    resolved INTEGER DEFAULT 0,
                    winning_outcome TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    timestamp_iso TEXT,
                    market_slug TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    price REAL NOT NULL,
                    best_bid REAL,
                    best_ask REAL,
                    session_id TEXT
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    trades_count INTEGER DEFAULT 0
                );
            """)

            # Migrate trades
            if trades_json.exists():
                try:
                    with open(trades_json, 'r') as f:
                        trades = json.load(f)
                    print(f"  Migrating {len(trades)} trades...")
                    for trade in trades:
                        try:
                            conn.execute("""
                                INSERT OR IGNORE INTO trades
                                (id, tx_hash, timestamp, wallet, wallet_name, role, side, outcome,
                                 shares, usdc, price, fee, market_slug, market_question, session_id, recorded_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                trade.get("id", ""),
                                trade.get("tx_hash", ""),
                                trade.get("timestamp", 0),
                                trade.get("wallet", ""),
                                trade.get("wallet_name", ""),
                                trade.get("role", "taker"),
                                trade.get("side", "BUY"),
                                trade.get("outcome", ""),
                                float(trade.get("shares", 0)),
                                float(trade.get("usdc", 0)),
                                float(trade.get("price", 0)),
                                float(trade.get("fee", 0)),
                                trade.get("market_slug", ""),
                                trade.get("market_question", ""),
                                trade.get("session_id", ""),
                                trade.get("recorded_at", datetime.now().isoformat())
                            ))
                        except Exception as e:
                            print(f"    Error migrating trade: {e}")
                    conn.commit()
                except Exception as e:
                    print(f"  Error reading trades.json: {e}")

            # Migrate positions
            if positions_json.exists():
                try:
                    with open(positions_json, 'r') as f:
                        positions = json.load(f)
                    print(f"  Migrating {len(positions)} positions...")
                    for key, pos in positions.items():
                        try:
                            conn.execute("""
                                INSERT OR REPLACE INTO positions
                                (wallet, market_slug, wallet_name, up_shares, down_shares,
                                 up_cost, down_cost, complete_sets, edge, hedge_ratio,
                                 total_trades, avg_up_price, avg_down_price, combined_price, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                pos.get("wallet", "").lower(),
                                pos.get("market_slug", ""),
                                pos.get("wallet_name", ""),
                                float(pos.get("up_shares", 0)),
                                float(pos.get("down_shares", 0)),
                                float(pos.get("up_cost", 0)),
                                float(pos.get("down_cost", 0)),
                                float(pos.get("complete_sets", 0)),
                                float(pos.get("edge", 0)),
                                float(pos.get("hedge_ratio", 0)),
                                int(pos.get("total_trades", 0)),
                                float(pos.get("avg_up_price", 0)),
                                float(pos.get("avg_down_price", 0)),
                                float(pos.get("combined_price", 0)),
                                pos.get("updated_at", datetime.now().isoformat())
                            ))
                        except Exception as e:
                            print(f"    Error migrating position: {e}")
                    conn.commit()
                except Exception as e:
                    print(f"  Error reading positions.json: {e}")

            # Migrate markets
            if markets_json.exists():
                try:
                    with open(markets_json, 'r') as f:
                        markets = json.load(f)
                    print(f"  Migrating {len(markets)} markets...")
                    for slug, market in markets.items():
                        try:
                            conn.execute("""
                                INSERT OR REPLACE INTO markets
                                (slug, question, condition_id, token_ids, outcomes,
                                 start_date, end_date, resolved, winning_outcome, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                market.get("slug", slug),
                                market.get("question", ""),
                                market.get("condition_id", ""),
                                json.dumps(market.get("token_ids", {})),
                                json.dumps(market.get("outcomes", [])),
                                market.get("start_date", ""),
                                market.get("end_date", ""),
                                1 if market.get("resolved") else 0,
                                market.get("winning_outcome", ""),
                                market.get("updated_at", datetime.now().isoformat())
                            ))
                        except Exception as e:
                            print(f"    Error migrating market: {e}")
                    conn.commit()
                except Exception as e:
                    print(f"  Error reading markets.json: {e}")

            conn.close()

            # Backup JSON files
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            for json_file in [trades_json, positions_json, markets_json,
                              self.db_dir / "prices.json", self.db_dir / "sessions.json"]:
                if json_file.exists():
                    backup_name = f"{json_file.stem}_{backup_time}.json.backup"
                    backup_path = self.backup_dir / backup_name
                    shutil.move(str(json_file), str(backup_path))
                    print(f"  Backed up {json_file.name} -> {backup_name}")

            print("Migration complete!")

    def _record_session_start(self):
        """Record new session in sessions table."""
        self.conn.execute("""
            INSERT OR REPLACE INTO sessions (session_id, started_at, ended_at, trades_count)
            VALUES (?, ?, NULL, 0)
        """, (self.session_id, self.session_start.isoformat()))
        self.conn.commit()

    def _create_backup(self, backup_type: str = "manual"):
        """Create a backup of the database."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"tracker_{backup_type}_{timestamp}.db"
        backup_path = self.backup_dir / backup_name

        try:
            # Use SQLite backup API for consistent backup
            backup_conn = sqlite3.connect(str(backup_path))
            self.conn.backup(backup_conn)
            backup_conn.close()
            print(f"Backup created: {backup_name}")

            # Clean up old backups (keep last 10)
            self._cleanup_old_backups()
            return str(backup_path)
        except Exception as e:
            print(f"Backup failed: {e}")
            return None

    def _cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backup files, keeping the most recent ones."""
        backups = sorted(self.backup_dir.glob("tracker_*.db"), key=os.path.getmtime, reverse=True)
        for backup in backups[keep_count:]:
            try:
                backup.unlink()
                print(f"Removed old backup: {backup.name}")
            except Exception as e:
                print(f"Failed to remove backup {backup.name}: {e}")

    def save_trade(self, trade: TradeEvent):
        """Save a single trade."""
        trade_key = f"{trade.tx_hash}:{trade.outcome}:{trade.shares}"
        if trade_key in self.session_trade_ids:
            return  # Skip duplicate

        self.session_trade_ids.add(trade_key)

        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO trades
                (id, tx_hash, timestamp, wallet, wallet_name, role, side, outcome,
                 shares, usdc, price, fee, market_slug, market_question, session_id, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.id,
                trade.tx_hash,
                trade.timestamp,
                trade.wallet,
                trade.wallet_name,
                trade.role,
                trade.side,
                trade.outcome,
                trade.shares,
                trade.usdc,
                trade.price,
                trade.fee,
                trade.market_slug,
                trade.market_question,
                self.session_id,
                datetime.now().isoformat()
            ))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving trade: {e}")

    def save_trades(self, trades: List[TradeEvent]):
        """Save multiple trades."""
        for trade in trades:
            self.save_trade(trade)

    def save_position(self, position: WalletPosition):
        """Save/update position."""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO positions
                (wallet, market_slug, wallet_name, up_shares, down_shares,
                 up_cost, down_cost, complete_sets, edge, hedge_ratio,
                 total_trades, avg_up_price, avg_down_price, combined_price, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.wallet.lower(),
                position.market_slug,
                position.wallet_name,
                position.up_shares,
                position.down_shares,
                position.up_cost,
                position.down_cost,
                position.complete_sets,
                position.edge,
                position.hedge_ratio,
                position.total_trades,
                position.avg_up_price,
                position.avg_down_price,
                position.combined_price,
                datetime.now().isoformat()
            ))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving position: {e}")

    def save_market(self, market: MarketContext):
        """Save/update market metadata."""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO markets
                (slug, question, condition_id, token_ids, outcomes,
                 start_date, end_date, resolved, winning_outcome, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                market.slug,
                market.question,
                market.condition_id,
                json.dumps(market.token_ids),
                json.dumps(market.outcomes),
                market.start_date.isoformat() if market.start_date else None,
                market.end_date.isoformat() if market.end_date else None,
                1 if market.resolved else 0,
                market.winning_outcome,
                datetime.now().isoformat()
            ))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving market: {e}")

    def save_price_update(
        self,
        market_slug: str,
        outcome: str,
        price: float,
        best_bid: float,
        best_ask: float,
        timestamp: int = None
    ):
        """Save a price update."""
        if timestamp is None:
            timestamp = int(datetime.now().timestamp())

        try:
            self.conn.execute("""
                INSERT INTO prices
                (timestamp, timestamp_iso, market_slug, outcome, price, best_bid, best_ask, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                datetime.fromtimestamp(timestamp).isoformat(),
                market_slug,
                outcome,
                price,
                best_bid,
                best_ask,
                self.session_id
            ))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving price: {e}")

    def get_all_trades(self) -> List[dict]:
        """Get all trades."""
        cursor = self.conn.execute("""
            SELECT * FROM trades ORDER BY timestamp DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_positions(self) -> Dict[str, dict]:
        """Get all positions as dict keyed by wallet:market_slug."""
        cursor = self.conn.execute("SELECT * FROM positions")
        positions = {}
        for row in cursor.fetchall():
            pos = dict(row)
            key = f"{pos['wallet']}:{pos['market_slug']}"
            positions[key] = pos
        return positions

    def get_all_markets(self) -> Dict[str, dict]:
        """Get all markets as dict keyed by slug."""
        cursor = self.conn.execute("SELECT * FROM markets")
        markets = {}
        for row in cursor.fetchall():
            market = dict(row)
            # Parse JSON fields
            market['token_ids'] = json.loads(market.get('token_ids', '{}'))
            market['outcomes'] = json.loads(market.get('outcomes', '[]'))
            market['resolved'] = bool(market.get('resolved', 0))
            markets[market['slug']] = market
        return markets

    def get_all_prices(self) -> List[dict]:
        """Get all price snapshots."""
        cursor = self.conn.execute("""
            SELECT * FROM prices ORDER BY timestamp DESC LIMIT 10000
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_prices_for_market(self, market_slug: str) -> List[dict]:
        """Get price snapshots for a specific market."""
        cursor = self.conn.execute("""
            SELECT * FROM prices WHERE market_slug = ? ORDER BY timestamp DESC LIMIT 1000
        """, (market_slug,))
        return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_prices(self, days: int = 7):
        """Delete prices older than specified days."""
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
        try:
            cursor = self.conn.execute("""
                DELETE FROM prices WHERE timestamp < ?
            """, (cutoff,))
            deleted = cursor.rowcount
            self.conn.commit()
            if deleted > 0:
                print(f"Cleaned up {deleted} old price records")
            return deleted
        except Exception as e:
            print(f"Error cleaning up prices: {e}")
            return 0

    def get_session_summary(self) -> dict:
        """Get summary of current session."""
        trades_count = self.conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        positions_count = self.conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        markets_count = self.conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0]

        return {
            "session_id": self.session_id,
            "db_dir": str(self.db_dir),
            "db_path": str(self.db_path),
            "session_trades_count": len(self.session_trade_ids),
            "total_trades_count": trades_count,
            "total_markets_count": markets_count,
            "total_positions_count": positions_count
        }

    def create_manual_backup(self) -> Optional[str]:
        """Create a manual backup (can be called via API)."""
        return self._create_backup("manual")

    def flush(self):
        """Update session end time and create shutdown backup."""
        try:
            self.conn.execute("""
                UPDATE sessions SET ended_at = ?, trades_count = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), len(self.session_trade_ids), self.session_id))
            self.conn.commit()

            # Create shutdown backup
            self._create_backup("shutdown")

            # Clean up old prices
            self.cleanup_old_prices()

            summary = self.get_session_summary()
            print(f"\nSession {self.session_id} saved: {summary['session_trades_count']} trades")
            print(f"Database: {summary['db_path']}")
        except Exception as e:
            print(f"Error during flush: {e}")

    def close(self):
        """Close database connection."""
        self.flush()
        self.conn.close()
