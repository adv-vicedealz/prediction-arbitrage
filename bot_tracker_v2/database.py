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

    # =========================================================================
    # ANALYTICS
    # =========================================================================

    def get_analytics_summary(self, wallet: Optional[str] = None) -> Dict:
        """Get aggregated analytics summary for resolved markets."""
        wallet_filter = "AND t.wallet = ?" if wallet else ""
        params = (wallet.lower(),) if wallet else ()

        with self._get_conn() as conn:
            # Get per-market P&L for resolved markets
            rows = conn.execute(f"""
                SELECT
                    t.market_slug,
                    m.winning_outcome,
                    m.end_time,
                    SUM(CASE WHEN t.outcome = 'Up' AND t.side = 'BUY' THEN t.shares ELSE 0 END) -
                    SUM(CASE WHEN t.outcome = 'Up' AND t.side = 'SELL' THEN t.shares ELSE 0 END) as up_net,
                    SUM(CASE WHEN t.outcome = 'Down' AND t.side = 'BUY' THEN t.shares ELSE 0 END) -
                    SUM(CASE WHEN t.outcome = 'Down' AND t.side = 'SELL' THEN t.shares ELSE 0 END) as down_net,
                    SUM(CASE WHEN t.side = 'BUY' THEN t.usdc ELSE 0 END) as total_cost,
                    SUM(CASE WHEN t.side = 'SELL' THEN t.usdc ELSE 0 END) as total_revenue,
                    SUM(t.usdc) as total_volume,
                    COUNT(*) as trades,
                    SUM(CASE WHEN t.role = 'maker' THEN 1 ELSE 0 END) as maker_trades
                FROM trades t
                JOIN markets m ON t.market_slug = m.slug
                WHERE m.resolved = 1 AND m.winning_outcome IS NOT NULL
                {wallet_filter}
                GROUP BY t.market_slug
            """, params).fetchall()

        if not rows:
            return {
                "total_pnl": 0, "win_rate": 0, "total_markets": 0,
                "winning_markets": 0, "losing_markets": 0, "total_volume": 0,
                "effective_edge": 0, "profit_factor": 0, "avg_win": 0, "avg_loss": 0,
                "avg_maker_ratio": 0, "btc_pnl": 0, "eth_pnl": 0, "btc_markets": 0, "eth_markets": 0
            }

        total_pnl = 0
        total_volume = 0
        gross_profit = 0
        gross_loss = 0
        wins = []
        losses = []
        btc_pnl = 0
        eth_pnl = 0
        btc_markets = 0
        eth_markets = 0
        maker_ratios = []

        for row in rows:
            r = dict(row)
            up_net = r["up_net"] or 0
            down_net = r["down_net"] or 0
            winner = r["winning_outcome"].lower() if r["winning_outcome"] else None
            cost = r["total_cost"] or 0
            revenue = r["total_revenue"] or 0
            volume = r["total_volume"] or 0
            trades = r["trades"] or 0
            maker = r["maker_trades"] or 0

            # Calculate payout based on winner
            if winner == "up":
                payout = up_net  # $1 per UP share
            elif winner == "down":
                payout = down_net  # $1 per DOWN share
            else:
                payout = 0

            pnl = payout + revenue - cost
            total_pnl += pnl
            total_volume += volume

            if pnl > 0:
                gross_profit += pnl
                wins.append(pnl)
            else:
                gross_loss += abs(pnl)
                losses.append(pnl)

            # Asset breakdown
            slug = r["market_slug"]
            if "btc" in slug.lower():
                btc_pnl += pnl
                btc_markets += 1
            elif "eth" in slug.lower():
                eth_pnl += pnl
                eth_markets += 1

            if trades > 0:
                maker_ratios.append(maker / trades)

        total_markets = len(rows)
        winning_markets = len(wins)
        losing_markets = len(losses)
        win_rate = winning_markets / total_markets if total_markets > 0 else 0
        effective_edge = (total_pnl / total_volume * 100) if total_volume > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        avg_maker_ratio = sum(maker_ratios) / len(maker_ratios) if maker_ratios else 0

        return {
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate * 100, 1),
            "total_markets": total_markets,
            "winning_markets": winning_markets,
            "losing_markets": losing_markets,
            "total_volume": round(total_volume, 2),
            "effective_edge": round(effective_edge, 3),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_maker_ratio": round(avg_maker_ratio * 100, 1),
            "btc_pnl": round(btc_pnl, 2),
            "eth_pnl": round(eth_pnl, 2),
            "btc_markets": btc_markets,
            "eth_markets": eth_markets
        }

    def get_markets_analytics(self, wallet: Optional[str] = None, asset: Optional[str] = None) -> List[Dict]:
        """Get per-market analytics for resolved markets."""
        wallet_filter = "AND t.wallet = ?" if wallet else ""
        asset_filter = ""
        params = []

        if wallet:
            params.append(wallet.lower())
        if asset:
            asset_filter = f"AND LOWER(t.market_slug) LIKE ?"
            params.append(f"%{asset.lower()}%")

        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT
                    t.market_slug,
                    m.question,
                    m.winning_outcome,
                    m.end_time,
                    SUM(CASE WHEN t.outcome = 'Up' AND t.side = 'BUY' THEN t.shares ELSE 0 END) -
                    SUM(CASE WHEN t.outcome = 'Up' AND t.side = 'SELL' THEN t.shares ELSE 0 END) as up_net,
                    SUM(CASE WHEN t.outcome = 'Down' AND t.side = 'BUY' THEN t.shares ELSE 0 END) -
                    SUM(CASE WHEN t.outcome = 'Down' AND t.side = 'SELL' THEN t.shares ELSE 0 END) as down_net,
                    SUM(CASE WHEN t.side = 'BUY' THEN t.usdc ELSE 0 END) as total_cost,
                    SUM(CASE WHEN t.side = 'SELL' THEN t.usdc ELSE 0 END) as total_revenue,
                    SUM(t.usdc) as total_volume,
                    COUNT(*) as trades,
                    SUM(CASE WHEN t.role = 'maker' THEN 1 ELSE 0 END) as maker_trades,
                    SUM(CASE WHEN t.outcome = 'Up' AND t.side = 'BUY' THEN t.usdc ELSE 0 END) as up_cost,
                    SUM(CASE WHEN t.outcome = 'Down' AND t.side = 'BUY' THEN t.usdc ELSE 0 END) as down_cost,
                    SUM(CASE WHEN t.outcome = 'Up' AND t.side = 'BUY' THEN t.shares ELSE 0 END) as up_bought,
                    SUM(CASE WHEN t.outcome = 'Down' AND t.side = 'BUY' THEN t.shares ELSE 0 END) as down_bought
                FROM trades t
                JOIN markets m ON t.market_slug = m.slug
                WHERE m.resolved = 1 AND m.winning_outcome IS NOT NULL
                {wallet_filter}
                {asset_filter}
                GROUP BY t.market_slug
                ORDER BY m.end_time DESC
            """, tuple(params)).fetchall()

        markets = []
        for row in rows:
            r = dict(row)
            up_net = r["up_net"] or 0
            down_net = r["down_net"] or 0
            winner = r["winning_outcome"].lower() if r["winning_outcome"] else None
            cost = r["total_cost"] or 0
            revenue = r["total_revenue"] or 0
            volume = r["total_volume"] or 0
            trades = r["trades"] or 0
            maker = r["maker_trades"] or 0
            up_cost = r["up_cost"] or 0
            down_cost = r["down_cost"] or 0
            up_bought = r["up_bought"] or 0
            down_bought = r["down_bought"] or 0
            slug = r["market_slug"]

            # Calculate payout based on winner
            if winner == "up":
                payout = up_net
            elif winner == "down":
                payout = down_net
            else:
                payout = 0

            pnl = payout + revenue - cost

            # Hedge ratio
            if up_net > 0 and down_net > 0:
                hedge_ratio = min(up_net, down_net) / max(up_net, down_net)
            elif up_net > 0 or down_net > 0:
                hedge_ratio = 0
            else:
                hedge_ratio = 1.0

            # Net bias
            if up_net > down_net + 100:
                net_bias = "UP"
            elif down_net > up_net + 100:
                net_bias = "DOWN"
            else:
                net_bias = "BALANCED"

            # Correct bias - did they have more of the winning side?
            if winner == "up":
                correct_bias = up_net >= down_net
            elif winner == "down":
                correct_bias = down_net >= up_net
            else:
                correct_bias = None

            # Average prices and edge
            avg_up_price = up_cost / up_bought if up_bought > 0 else 0
            avg_down_price = down_cost / down_bought if down_bought > 0 else 0
            combined_price = avg_up_price + avg_down_price if up_bought > 0 and down_bought > 0 else 0
            edge = (1.0 - combined_price) * 100 if combined_price > 0 else 0

            # Asset type
            asset_type = "BTC" if "btc" in slug.lower() else "ETH" if "eth" in slug.lower() else "OTHER"

            markets.append({
                "slug": slug,
                "asset": asset_type,
                "question": r["question"] or "",
                "winner": winner,
                "end_time": datetime.utcfromtimestamp(r["end_time"]).isoformat() + "Z" if r["end_time"] else None,
                "pnl": round(pnl, 2),
                "trades": trades,
                "volume": round(volume, 2),
                "maker_ratio": round(maker / trades * 100, 1) if trades > 0 else 0,
                "hedge_ratio": round(hedge_ratio * 100, 1),
                "edge": round(edge, 2),
                "up_net": round(up_net, 2),
                "down_net": round(down_net, 2),
                "net_bias": net_bias,
                "correct_bias": correct_bias,
                "avg_up_price": round(avg_up_price, 4),
                "avg_down_price": round(avg_down_price, 4),
                "combined_price": round(combined_price, 4)
            })

        return markets

    def get_pnl_over_time(self, wallet: Optional[str] = None) -> List[Dict]:
        """Get cumulative P&L by market end time for resolved markets."""
        markets = self.get_markets_analytics(wallet)

        # Sort by end_time
        markets.sort(key=lambda x: x["end_time"] or "")

        cumulative_pnl = 0
        timeline = []

        for m in markets:
            cumulative_pnl += m["pnl"]
            timeline.append({
                "timestamp": m["end_time"],
                "market_slug": m["slug"],
                "asset": m["asset"],
                "winner": m["winner"],
                "pnl": m["pnl"],
                "cumulative_pnl": round(cumulative_pnl, 2)
            })

        return timeline

    def get_market_trades_timeline(self, market_slug: str) -> List[Dict]:
        """Get trades for a market with running position totals."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT
                    t.*,
                    m.winning_outcome
                FROM trades t
                LEFT JOIN markets m ON t.market_slug = m.slug
                WHERE t.market_slug = ?
                ORDER BY t.timestamp ASC
            """, (market_slug,)).fetchall()

        trades = []
        cumulative_up = 0
        cumulative_down = 0
        cumulative_cost = 0
        cumulative_revenue = 0

        for row in rows:
            r = dict(row)

            # Update running totals
            if r["side"] == "BUY":
                if r["outcome"] == "Up":
                    cumulative_up += r["shares"]
                else:
                    cumulative_down += r["shares"]
                cumulative_cost += r["usdc"]
            else:  # SELL
                if r["outcome"] == "Up":
                    cumulative_up -= r["shares"]
                else:
                    cumulative_down -= r["shares"]
                cumulative_revenue += r["usdc"]

            trades.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "timestamp_iso": datetime.utcfromtimestamp(r["timestamp"]).isoformat() + "Z",
                "side": r["side"],
                "outcome": r["outcome"],
                "role": r["role"],
                "shares": r["shares"],
                "price": r["price"],
                "usdc": r["usdc"],
                "cumulative_up": round(cumulative_up, 2),
                "cumulative_down": round(cumulative_down, 2),
                "net_position": round(cumulative_up - cumulative_down, 2),
                "cumulative_cost": round(cumulative_cost, 2),
                "cumulative_revenue": round(cumulative_revenue, 2)
            })

        return trades

    def get_price_execution_analysis(self, wallet: Optional[str] = None) -> Dict:
        """Analyze trade execution prices vs market prices."""
        wallet_filter = "AND t.wallet = ?" if wallet else ""
        params = (wallet.lower(),) if wallet else ()

        with self._get_conn() as conn:
            # Get all trades with their prices and try to match with price snapshots
            trades_rows = conn.execute(f"""
                SELECT
                    t.id,
                    t.timestamp,
                    t.market_slug,
                    t.outcome,
                    t.side,
                    t.role,
                    t.price,
                    t.shares,
                    t.usdc
                FROM trades t
                WHERE 1=1
                {wallet_filter}
                ORDER BY t.timestamp
            """, params).fetchall()

            # Get all price snapshots for comparison
            prices_rows = conn.execute("""
                SELECT
                    timestamp,
                    market_slug,
                    outcome,
                    price as market_price,
                    best_bid,
                    best_ask
                FROM prices
                ORDER BY timestamp
            """).fetchall()

        if not trades_rows:
            return {
                "total_trades": 0,
                "trades_with_price_data": 0,
                "avg_spread_captured": 0,
                "pct_at_bid": 0,
                "pct_at_ask": 0,
                "pct_between": 0,
                "avg_combined_cost": 0,
                "combined_cost_distribution": [],
                "maker_savings": 0,
                "order_placement_analysis": []
            }

        # Build price index for quick lookup
        price_index = {}
        for row in prices_rows:
            r = dict(row)
            key = (r["market_slug"], r["outcome"])
            if key not in price_index:
                price_index[key] = []
            price_index[key].append({
                "timestamp": r["timestamp"],
                "market_price": r["market_price"],
                "best_bid": r["best_bid"],
                "best_ask": r["best_ask"]
            })

        # Analyze each trade
        total_trades = len(trades_rows)
        trades_with_price = 0
        at_bid = 0
        at_ask = 0
        between = 0
        spread_captured_sum = 0

        # Track combined costs per market for distribution
        market_costs = {}  # market_slug -> {up_cost, down_cost, up_shares, down_shares}

        for trade_row in trades_rows:
            t = dict(trade_row)
            key = (t["market_slug"], t["outcome"])

            # Find closest price snapshot
            if key in price_index:
                price_snapshots = price_index[key]
                closest = min(price_snapshots, key=lambda p: abs(p["timestamp"] - t["timestamp"]))

                # Only use if within 60 seconds
                if abs(closest["timestamp"] - t["timestamp"]) <= 60:
                    trades_with_price += 1
                    trade_price = t["price"]
                    best_bid = closest["best_bid"]
                    best_ask = closest["best_ask"]

                    if t["side"] == "BUY":
                        # For BUY: closer to bid is better (buying lower)
                        if trade_price <= best_bid * 1.01:  # Within 1% of bid
                            at_bid += 1
                            spread_captured_sum += (best_ask - trade_price)
                        elif trade_price >= best_ask * 0.99:  # Within 1% of ask
                            at_ask += 1
                        else:
                            between += 1
                            spread_captured_sum += (best_ask - trade_price)

            # Track market costs
            if t["side"] == "BUY":
                if t["market_slug"] not in market_costs:
                    market_costs[t["market_slug"]] = {
                        "up_cost": 0, "down_cost": 0, "up_shares": 0, "down_shares": 0
                    }
                mc = market_costs[t["market_slug"]]
                if t["outcome"] == "Up":
                    mc["up_cost"] += t["usdc"]
                    mc["up_shares"] += t["shares"]
                else:
                    mc["down_cost"] += t["usdc"]
                    mc["down_shares"] += t["shares"]

        # Calculate combined cost distribution
        combined_costs = []
        for slug, mc in market_costs.items():
            if mc["up_shares"] > 0 and mc["down_shares"] > 0:
                avg_up = mc["up_cost"] / mc["up_shares"]
                avg_down = mc["down_cost"] / mc["down_shares"]
                combined = avg_up + avg_down
                combined_costs.append({
                    "market_slug": slug,
                    "combined_cost": combined,
                    "avg_up": avg_up,
                    "avg_down": avg_down
                })

        # Create distribution buckets
        buckets = {}
        for cc in combined_costs:
            bucket = round(cc["combined_cost"], 2)
            bucket_str = f"${bucket:.2f}"
            if bucket_str not in buckets:
                buckets[bucket_str] = 0
            buckets[bucket_str] += 1

        # Sort buckets
        distribution = [{"bucket": k, "count": v} for k, v in sorted(buckets.items())]

        # Calculate averages
        avg_spread = spread_captured_sum / trades_with_price if trades_with_price > 0 else 0
        avg_combined = sum(cc["combined_cost"] for cc in combined_costs) / len(combined_costs) if combined_costs else 0
        pct_below_dollar = len([cc for cc in combined_costs if cc["combined_cost"] < 1.0]) / len(combined_costs) * 100 if combined_costs else 0

        return {
            "total_trades": total_trades,
            "trades_with_price_data": trades_with_price,
            "avg_spread_captured": round(avg_spread, 4),
            "pct_at_bid": round(at_bid / trades_with_price * 100, 1) if trades_with_price > 0 else 0,
            "pct_at_ask": round(at_ask / trades_with_price * 100, 1) if trades_with_price > 0 else 0,
            "pct_between": round(between / trades_with_price * 100, 1) if trades_with_price > 0 else 0,
            "avg_combined_cost": round(avg_combined, 4),
            "pct_below_dollar": round(pct_below_dollar, 1),
            "combined_cost_distribution": distribution,
            "markets_analyzed": len(combined_costs),
            "order_placement_analysis": combined_costs[:20]  # Top 20 for reference
        }
