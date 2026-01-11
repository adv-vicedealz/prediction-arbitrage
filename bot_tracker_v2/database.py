"""
SQLite database operations for Bot Tracker v2.
Single source of truth with WAL mode and automatic backups.
"""

import sqlite3
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

from .config import DB_PATH, BACKUP_DIR, BACKUP_KEEP_DAYS, ensure_dirs, TARGET_WALLETS
from .logger import setup_logger

log = setup_logger(__name__)


SCHEMA = """
-- Markets we're tracking
CREATE TABLE IF NOT EXISTS markets (
    slug TEXT PRIMARY KEY,
    condition_id TEXT NOT NULL,
    question TEXT,
    start_time INTEGER,
    end_time INTEGER,
    up_token_id TEXT,
    down_token_id TEXT,
    resolved INTEGER DEFAULT 0,
    winning_outcome TEXT,
    trades_fetched INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- All trades from target wallets
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    tx_hash TEXT,
    timestamp INTEGER,
    wallet TEXT,
    wallet_name TEXT,
    role TEXT,  -- 'maker' or 'taker'
    side TEXT,  -- 'BUY' or 'SELL'
    outcome TEXT,  -- 'Up' or 'Down'
    shares REAL,
    price REAL,
    usdc REAL,
    fee REAL DEFAULT 0,  -- Store fee but don't include in P&L
    market_slug TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (market_slug) REFERENCES markets(slug)
);

-- Live price snapshots
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER,
    market_slug TEXT,
    outcome TEXT,
    price REAL,
    best_bid REAL,
    best_ask REAL,
    FOREIGN KEY (market_slug) REFERENCES markets(slug)
);

-- Tracked wallets
CREATE TABLE IF NOT EXISTS wallets (
    address TEXT PRIMARY KEY,
    name TEXT,
    active INTEGER DEFAULT 1
);

-- Top traders list
CREATE TABLE IF NOT EXISTS traders (
    wallet TEXT PRIMARY KEY,
    name TEXT,
    link TEXT,
    all_time_profit REAL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_slug);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet);
CREATE INDEX IF NOT EXISTS idx_trades_role ON trades(role);
CREATE INDEX IF NOT EXISTS idx_prices_market ON prices(market_slug);
CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON prices(timestamp);
CREATE INDEX IF NOT EXISTS idx_markets_end_time ON markets(end_time);
CREATE INDEX IF NOT EXISTS idx_markets_trades_fetched ON markets(trades_fetched);
"""


class Database:
    """SQLite database with WAL mode and automatic backups."""

    def __init__(self, db_path: Path = DB_PATH):
        ensure_dirs()
        self.db_path = db_path
        self._init_db()
        self._init_wallets()

    def _init_db(self):
        """Initialize database with schema."""
        with self._get_conn() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(SCHEMA)
            conn.commit()
        log.info(f"Database initialized: {self.db_path}")

    def _init_wallets(self):
        """Initialize target wallets from config."""
        with self._get_conn() as conn:
            for address, name in TARGET_WALLETS.items():
                conn.execute(
                    "INSERT OR REPLACE INTO wallets (address, name, active) VALUES (?, ?, 1)",
                    (address.lower(), name)
                )
            conn.commit()

    @contextmanager
    def _get_conn(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # =========================================================================
    # MARKET OPERATIONS
    # =========================================================================

    def save_market(self, market: Dict[str, Any]) -> None:
        """Save or update a market."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO markets
                (slug, condition_id, question, start_time, end_time,
                 up_token_id, down_token_id, resolved, winning_outcome, trades_fetched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                market["slug"],
                market["condition_id"],
                market.get("question", ""),
                market.get("start_time"),
                market.get("end_time"),
                market.get("up_token_id"),
                market.get("down_token_id"),
                market.get("resolved", 0),
                market.get("winning_outcome"),
                market.get("trades_fetched", 0)
            ))
            conn.commit()

    def get_market(self, slug: str) -> Optional[Dict]:
        """Get a market by slug."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM markets WHERE slug = ?", (slug,)
            ).fetchone()
            return dict(row) if row else None

    def get_markets_to_fetch(self) -> List[Dict]:
        """Get markets that are ready for trade fetching."""
        now = int(time.time())
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM markets
                WHERE trades_fetched = 0
                AND end_time IS NOT NULL
                AND end_time < ?
                ORDER BY end_time ASC
            """, (now,)).fetchall()
            return [dict(row) for row in rows]

    def mark_market_fetched(self, slug: str, winning_outcome: Optional[str] = None) -> None:
        """Mark a market as having its trades fetched."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE markets
                SET trades_fetched = 1, resolved = 1, winning_outcome = ?
                WHERE slug = ?
            """, (winning_outcome, slug))
            conn.commit()

    def get_active_markets(self) -> List[Dict]:
        """Get markets that are not yet resolved."""
        now = int(time.time())
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM markets
                WHERE (end_time IS NULL OR end_time > ?)
                AND trades_fetched = 0
            """, (now,)).fetchall()
            return [dict(row) for row in rows]

    def market_exists(self, slug: str) -> bool:
        """Check if a market exists in the database."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM markets WHERE slug = ?", (slug,)
            ).fetchone()
            return row is not None

    # =========================================================================
    # TRADE OPERATIONS
    # =========================================================================

    def save_trade(self, trade: Dict[str, Any]) -> bool:
        """Save a trade. Returns True if new, False if duplicate."""
        with self._get_conn() as conn:
            try:
                conn.execute("""
                    INSERT INTO trades
                    (id, tx_hash, timestamp, wallet, wallet_name, role, side, outcome,
                     shares, price, usdc, fee, market_slug)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade["id"],
                    trade.get("tx_hash", ""),
                    trade["timestamp"],
                    trade["wallet"].lower(),
                    trade.get("wallet_name", ""),
                    trade.get("role", "taker"),  # maker or taker
                    trade["side"],  # BUY or SELL
                    trade["outcome"],  # Up or Down
                    trade["shares"],
                    trade["price"],
                    trade.get("usdc", trade["shares"] * trade["price"]),
                    trade.get("fee", 0),  # Fee stored but not in P&L
                    trade["market_slug"]
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Duplicate

    def save_trades(self, trades: List[Dict[str, Any]]) -> int:
        """Save multiple trades. Returns count of new trades."""
        new_count = 0
        for trade in trades:
            if self.save_trade(trade):
                new_count += 1
        return new_count

    def get_trades(self, limit: int = 2000, market_slug: Optional[str] = None) -> List[Dict]:
        """Get recent trades, optionally filtered by market."""
        with self._get_conn() as conn:
            if market_slug:
                rows = conn.execute("""
                    SELECT * FROM trades
                    WHERE market_slug = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (market_slug, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM trades
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_trade_count(self) -> int:
        """Get total trade count."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM trades").fetchone()
            return row[0]

    # =========================================================================
    # POSITION COMPUTATION (from trades)
    # =========================================================================

    def get_positions(self) -> List[Dict]:
        """Compute positions from trades (not stored, calculated on demand)."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT
                    wallet,
                    wallet_name,
                    market_slug,
                    SUM(CASE WHEN outcome = 'Up' AND side = 'BUY' THEN shares ELSE 0 END) -
                    SUM(CASE WHEN outcome = 'Up' AND side = 'SELL' THEN shares ELSE 0 END) as up_shares,
                    SUM(CASE WHEN outcome = 'Down' AND side = 'BUY' THEN shares ELSE 0 END) -
                    SUM(CASE WHEN outcome = 'Down' AND side = 'SELL' THEN shares ELSE 0 END) as down_shares,
                    SUM(CASE WHEN outcome = 'Up' AND side = 'BUY' THEN usdc ELSE 0 END) as up_cost,
                    SUM(CASE WHEN outcome = 'Down' AND side = 'BUY' THEN usdc ELSE 0 END) as down_cost,
                    SUM(CASE WHEN outcome = 'Up' AND side = 'SELL' THEN usdc ELSE 0 END) as up_revenue,
                    SUM(CASE WHEN outcome = 'Down' AND side = 'SELL' THEN usdc ELSE 0 END) as down_revenue,
                    SUM(CASE WHEN outcome = 'Up' AND side = 'BUY' THEN shares ELSE 0 END) as up_bought,
                    SUM(CASE WHEN outcome = 'Down' AND side = 'BUY' THEN shares ELSE 0 END) as down_bought,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
                    SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
                    SUM(CASE WHEN role = 'maker' THEN 1 ELSE 0 END) as maker_trades,
                    SUM(CASE WHEN role = 'taker' THEN 1 ELSE 0 END) as taker_trades,
                    SUM(COALESCE(fee, 0)) as total_fees,
                    MIN(timestamp) as first_trade_ts,
                    MAX(timestamp) as last_trade_ts
                FROM trades
                GROUP BY wallet, market_slug
            """).fetchall()

        positions = []
        for row in rows:
            r = dict(row)
            up_shares = max(0, r["up_shares"] or 0)
            down_shares = max(0, r["down_shares"] or 0)
            up_bought = r["up_bought"] or 0
            down_bought = r["down_bought"] or 0

            # Compute derived fields
            complete_sets = min(up_shares, down_shares)
            unhedged_up = max(0, up_shares - down_shares)
            unhedged_down = max(0, down_shares - up_shares)

            avg_up_price = r["up_cost"] / up_bought if up_bought > 0 else 0
            avg_down_price = r["down_cost"] / down_bought if down_bought > 0 else 0

            combined_price = avg_up_price + avg_down_price if up_bought > 0 and down_bought > 0 else 0
            edge = 1.0 - combined_price if combined_price > 0 else 0

            if up_shares > 0 and down_shares > 0:
                hedge_ratio = min(up_shares, down_shares) / max(up_shares, down_shares)
            elif up_shares > 0 or down_shares > 0:
                hedge_ratio = 0
            else:
                hedge_ratio = 1.0

            positions.append({
                "wallet": r["wallet"],
                "wallet_name": r["wallet_name"],
                "market_slug": r["market_slug"],
                "up_shares": up_shares,
                "down_shares": down_shares,
                "up_cost": r["up_cost"] or 0,
                "down_cost": r["down_cost"] or 0,
                "up_revenue": r["up_revenue"] or 0,
                "down_revenue": r["down_revenue"] or 0,
                "complete_sets": complete_sets,
                "unhedged_up": unhedged_up,
                "unhedged_down": unhedged_down,
                "avg_up_price": avg_up_price,
                "avg_down_price": avg_down_price,
                "combined_price": combined_price,
                "edge": edge,
                "hedge_ratio": hedge_ratio,
                "total_trades": r["total_trades"],
                "buy_trades": r["buy_trades"],
                "sell_trades": r["sell_trades"],
                "maker_trades": r["maker_trades"] or 0,
                "taker_trades": r["taker_trades"] or 0,
                "total_fees": r["total_fees"] or 0,  # Stored for reference, not in P&L
                "first_trade_ts": r["first_trade_ts"],
                "last_trade_ts": r["last_trade_ts"]
            })

        return positions

    # =========================================================================
    # PRICE OPERATIONS
    # =========================================================================

    def save_price(self, price: Dict[str, Any]) -> None:
        """Save a price snapshot."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO prices
                (timestamp, market_slug, outcome, price, best_bid, best_ask)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                price["timestamp"],
                price["market_slug"],
                price["outcome"],
                price["price"],
                price.get("best_bid", 0),
                price.get("best_ask", 0)
            ))
            conn.commit()

    def get_prices(self, limit: int = 50, market_slug: Optional[str] = None) -> List[Dict]:
        """Get recent prices."""
        with self._get_conn() as conn:
            if market_slug:
                rows = conn.execute("""
                    SELECT * FROM prices
                    WHERE market_slug = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (market_slug, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM prices
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,)).fetchall()

        result = []
        for row in rows:
            r = dict(row)
            r["timestamp_iso"] = datetime.utcfromtimestamp(r["timestamp"]).isoformat() + "Z"
            result.append(r)
        return result

    def cleanup_old_prices(self, hours: int = 24) -> int:
        """Delete prices older than X hours. Returns count deleted."""
        cutoff = int(time.time()) - (hours * 3600)
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM prices WHERE timestamp < ?", (cutoff,))
            conn.commit()
            return cursor.rowcount

    def get_price_counts_by_market(self) -> Dict[str, int]:
        """Get count of price snapshots per market."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT market_slug, COUNT(*) as count
                FROM prices
                GROUP BY market_slug
            """).fetchall()
            return {row["market_slug"]: row["count"] for row in rows}

    # =========================================================================
    # WALLET OPERATIONS
    # =========================================================================

    def get_wallets(self) -> List[Dict]:
        """Get all tracked wallets."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT address, name FROM wallets WHERE active = 1"
            ).fetchall()
            return [dict(row) for row in rows]

    def update_wallet(self, address: str, name: str) -> None:
        """Update or add a wallet."""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO wallets (address, name, active) VALUES (?, ?, 1)",
                (address.lower(), name)
            )
            conn.commit()

    # =========================================================================
    # TRADER OPERATIONS
    # =========================================================================

    def get_traders(self) -> List[Dict]:
        """Get all top traders."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM traders").fetchall()
            return [dict(row) for row in rows]

    def save_trader(self, trader: Dict[str, Any]) -> None:
        """Save a trader."""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO traders (wallet, name, link, all_time_profit) VALUES (?, ?, ?, ?)",
                (trader["wallet"].lower(), trader["name"], trader.get("link", ""), trader.get("all_time_profit", 0))
            )
            conn.commit()

    def delete_trader(self, wallet: str) -> bool:
        """Delete a trader. Returns True if deleted."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM traders WHERE wallet = ?", (wallet.lower(),))
            conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # TRACKING INFO
    # =========================================================================

    def get_tracking_info(self, start_time: datetime) -> Dict:
        """Get tracking info for dashboard."""
        with self._get_conn() as conn:
            # Get trades grouped by market
            market_rows = conn.execute("""
                SELECT
                    t.market_slug,
                    m.question,
                    m.end_time,
                    m.resolved,
                    m.winning_outcome,
                    COUNT(*) as trades_captured,
                    MIN(t.timestamp) as first_trade_time,
                    MAX(t.timestamp) as last_trade_time
                FROM trades t
                LEFT JOIN markets m ON t.market_slug = m.slug
                GROUP BY t.market_slug
                ORDER BY MAX(t.timestamp) DESC
            """).fetchall()

            total_trades = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]

        markets = []
        for row in market_rows:
            r = dict(row)
            first_ts = r["first_trade_time"]
            last_ts = r["last_trade_time"]

            markets.append({
                "slug": r["market_slug"],
                "question": r["question"] or "",
                "trades_captured": r["trades_captured"],
                "first_trade_time": datetime.utcfromtimestamp(first_ts).isoformat() + "Z" if first_ts else None,
                "last_trade_time": datetime.utcfromtimestamp(last_ts).isoformat() + "Z" if last_ts else None,
                "tracking_duration_mins": (last_ts - first_ts) / 60 if first_ts and last_ts else 0,
                "market_end_time": datetime.utcfromtimestamp(r["end_time"]).isoformat() + "Z" if r["end_time"] else None,
                "resolved": bool(r["resolved"]),
                "winning_outcome": r["winning_outcome"]
            })

        return {
            "tracking_started": start_time.isoformat() + "Z",
            "uptime_seconds": (datetime.utcnow() - start_time).total_seconds(),
            "total_trades_captured": total_trades,
            "markets": markets
        }

    # =========================================================================
    # BACKUP
    # =========================================================================

    def backup(self) -> Optional[Path]:
        """Create a database backup. Returns backup path."""
        if not self.db_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"tracker_v2_{timestamp}.db"

        try:
            # Use SQLite backup API
            with self._get_conn() as conn:
                backup_conn = sqlite3.connect(str(backup_path))
                conn.backup(backup_conn)
                backup_conn.close()

            log.info(f"Database backup created: {backup_path}")

            # Cleanup old backups
            self._cleanup_old_backups()

            return backup_path
        except Exception as e:
            log.error(f"Backup failed: {e}")
            return None

    def _cleanup_old_backups(self):
        """Remove backups older than BACKUP_KEEP_DAYS."""
        cutoff = time.time() - (BACKUP_KEEP_DAYS * 86400)
        for backup_file in BACKUP_DIR.glob("tracker_v2_*.db"):
            if backup_file.stat().st_mtime < cutoff:
                backup_file.unlink()
                log.info(f"Old backup removed: {backup_file}")
