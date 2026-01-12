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

    # =========================================================================
    # DEEP ANALYSIS
    # =========================================================================

    def get_resolved_markets_list(self) -> List[Dict]:
        """Get list of all markets with trades for the market selector dropdown."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT
                    m.slug,
                    m.question,
                    m.end_time,
                    m.winning_outcome,
                    m.resolved,
                    COUNT(t.id) as trade_count
                FROM markets m
                LEFT JOIN trades t ON m.slug = t.market_slug
                GROUP BY m.slug
                HAVING trade_count > 0
                ORDER BY m.end_time DESC NULLS LAST
            """).fetchall()

        return [{
            "slug": r["slug"],
            "question": r["question"] or "",
            "end_time": datetime.utcfromtimestamp(r["end_time"]).isoformat() + "Z" if r["end_time"] else None,
            "winner": r["winning_outcome"].lower() if r["winning_outcome"] else None,
            "trade_count": r["trade_count"]
        } for r in rows]

    def get_trade_execution_quality(self, market_slug: Optional[str] = None) -> Dict:
        """Match each trade with closest price snapshot, calculate execution quality score."""
        market_filter = "AND t.market_slug = ?" if market_slug else ""
        params = (market_slug,) if market_slug else ()

        with self._get_conn() as conn:
            # Get all trades with market timing info
            trades_rows = conn.execute(f"""
                SELECT
                    t.id,
                    t.timestamp,
                    t.market_slug,
                    t.outcome,
                    t.side,
                    t.role,
                    t.price as trade_price,
                    t.shares,
                    t.usdc,
                    m.start_time,
                    m.end_time
                FROM trades t
                JOIN markets m ON t.market_slug = m.slug
                WHERE m.resolved = 1
                {market_filter}
                ORDER BY t.timestamp
            """, params).fetchall()

            # Get price snapshots
            prices_rows = conn.execute("""
                SELECT timestamp, market_slug, outcome, price, best_bid, best_ask
                FROM prices
                ORDER BY timestamp
            """).fetchall()

        empty_result = {
            "trades": [],
            "summary": {
                "total_trades": 0,
                "matched_trades": 0,
                "avg_execution_score": 0,
                "pct_at_bid": 0,
                "pct_at_ask": 0,
                "pct_mid": 0,
                "maker_avg_score": 0,
                "taker_avg_score": 0
            },
            "distribution": [],
            "time_analysis": {
                "by_minute": [],
                "early_avg": 0,
                "late_avg": 0,
                "degradation_pct": 0
            },
            "slippage": {
                "total_usd": 0,
                "by_role": {"maker": 0, "taker": 0},
                "by_outcome": {"up": 0, "down": 0},
                "by_side": {"buy": 0, "sell": 0},
                "avg_per_trade": 0
            },
            "size_analysis": {
                "correlation": 0,
                "by_bucket": {"small": 0, "medium": 0, "large": 0}
            },
            "breakdown": {
                "buy_up": 0, "buy_down": 0,
                "sell_up": 0, "sell_down": 0
            }
        }

        if not trades_rows:
            return empty_result

        # Build price index
        price_index = {}
        for row in prices_rows:
            r = dict(row)
            key = (r["market_slug"], r["outcome"])
            if key not in price_index:
                price_index[key] = []
            price_index[key].append({
                "timestamp": r["timestamp"],
                "price": r["price"],
                "best_bid": r["best_bid"],
                "best_ask": r["best_ask"]
            })

        # Analyze each trade
        matched_trades = []
        scores = []
        maker_scores = []
        taker_scores = []
        at_bid = 0
        at_ask = 0
        mid_range = 0

        # NEW: Time analysis data
        minute_scores = {}  # {minute: {"all": [], "maker": [], "taker": []}}

        # NEW: Slippage data
        slippage_total = 0
        slippage_maker = 0
        slippage_taker = 0
        slippage_up = 0
        slippage_down = 0
        slippage_buy = 0
        slippage_sell = 0

        # NEW: Size analysis data
        size_score_pairs = []  # [(shares, score), ...]
        small_scores = []  # shares < 50
        medium_scores = []  # 50 <= shares < 200
        large_scores = []  # shares >= 200

        # NEW: Breakdown data
        breakdown_scores = {
            "buy_up": [], "buy_down": [],
            "sell_up": [], "sell_down": []
        }

        for trade_row in trades_rows:
            t = dict(trade_row)
            key = (t["market_slug"], t["outcome"])

            trade_data = {
                "id": t["id"],
                "timestamp": t["timestamp"],
                "market_slug": t["market_slug"],
                "outcome": t["outcome"],
                "side": t["side"],
                "role": t["role"],
                "trade_price": t["trade_price"],
                "shares": t["shares"],
                "market_bid": None,
                "market_ask": None,
                "market_mid": None,
                "execution_score": None
            }

            # Calculate minute into market for time analysis
            if "15m" in t["market_slug"]:
                actual_start = t["end_time"] - 900
            else:
                actual_start = t["start_time"]
            minute_into_market = max(0, min(14, int((t["timestamp"] - actual_start) / 60)))

            if key in price_index:
                price_snapshots = price_index[key]
                closest = min(price_snapshots, key=lambda p: abs(p["timestamp"] - t["timestamp"]))

                if abs(closest["timestamp"] - t["timestamp"]) <= 60:
                    best_bid = closest["best_bid"]
                    best_ask = closest["best_ask"]
                    spread = best_ask - best_bid
                    mid_price = (best_bid + best_ask) / 2

                    trade_data["market_bid"] = best_bid
                    trade_data["market_ask"] = best_ask
                    trade_data["market_mid"] = mid_price

                    # Execution score: 0 = at bid, 1 = at ask
                    if spread > 0:
                        score = (t["trade_price"] - best_bid) / spread
                        score = max(0, min(1, score))  # Clamp to 0-1
                    else:
                        score = 0.5

                    trade_data["execution_score"] = round(score, 4)
                    scores.append(score)

                    if t["role"] == "maker":
                        maker_scores.append(score)
                    else:
                        taker_scores.append(score)

                    # Categorize
                    if score <= 0.1:
                        at_bid += 1
                    elif score >= 0.9:
                        at_ask += 1
                    else:
                        mid_range += 1

                    # NEW: Time analysis - group scores by minute
                    if minute_into_market not in minute_scores:
                        minute_scores[minute_into_market] = {"all": [], "maker": [], "taker": []}
                    minute_scores[minute_into_market]["all"].append(score)
                    if t["role"] == "maker":
                        minute_scores[minute_into_market]["maker"].append(score)
                    else:
                        minute_scores[minute_into_market]["taker"].append(score)

                    # NEW: Slippage calculation
                    # For BUY: slippage = (trade_price - mid) * shares (positive = overpaid)
                    # For SELL: slippage = (mid - trade_price) * shares (positive = undersold)
                    if t["side"] == "BUY":
                        slip = (t["trade_price"] - mid_price) * t["shares"]
                    else:
                        slip = (mid_price - t["trade_price"]) * t["shares"]

                    slippage_total += slip
                    if t["role"] == "maker":
                        slippage_maker += slip
                    else:
                        slippage_taker += slip
                    if t["outcome"] == "Up":
                        slippage_up += slip
                    else:
                        slippage_down += slip
                    if t["side"] == "BUY":
                        slippage_buy += slip
                    else:
                        slippage_sell += slip

                    # NEW: Size analysis
                    size_score_pairs.append((t["shares"], score))
                    if t["shares"] < 50:
                        small_scores.append(score)
                    elif t["shares"] < 200:
                        medium_scores.append(score)
                    else:
                        large_scores.append(score)

                    # NEW: Breakdown by side+outcome
                    breakdown_key = f"{t['side'].lower()}_{t['outcome'].lower()}"
                    breakdown_scores[breakdown_key].append(score)

            matched_trades.append(trade_data)

        # Create distribution histogram (10 buckets from 0 to 1)
        distribution = []
        for i in range(10):
            bucket_start = i / 10
            bucket_end = (i + 1) / 10
            count = len([s for s in scores if bucket_start <= s < bucket_end])
            distribution.append({
                "bucket": f"{bucket_start:.1f}-{bucket_end:.1f}",
                "start": bucket_start,
                "end": bucket_end,
                "count": count
            })

        matched_count = len(scores)

        # NEW: Build time analysis
        by_minute = []
        early_scores = []
        late_scores = []
        for minute in range(15):
            if minute in minute_scores:
                data = minute_scores[minute]
                avg_all = sum(data["all"]) / len(data["all"]) if data["all"] else 0
                avg_maker = sum(data["maker"]) / len(data["maker"]) if data["maker"] else 0
                avg_taker = sum(data["taker"]) / len(data["taker"]) if data["taker"] else 0
                by_minute.append({
                    "minute": minute,
                    "avg_score": round(avg_all, 4),
                    "maker_avg": round(avg_maker, 4),
                    "taker_avg": round(avg_taker, 4),
                    "trade_count": len(data["all"])
                })
                # Collect early (0-4) and late (10-14) scores
                if minute < 5:
                    early_scores.extend(data["all"])
                elif minute >= 10:
                    late_scores.extend(data["all"])
            else:
                by_minute.append({
                    "minute": minute,
                    "avg_score": 0,
                    "maker_avg": 0,
                    "taker_avg": 0,
                    "trade_count": 0
                })

        early_avg = sum(early_scores) / len(early_scores) if early_scores else 0
        late_avg = sum(late_scores) / len(late_scores) if late_scores else 0
        degradation_pct = ((late_avg - early_avg) / early_avg * 100) if early_avg > 0 else 0

        # NEW: Calculate size-execution correlation (Pearson)
        correlation = 0
        if len(size_score_pairs) > 1:
            sizes = [p[0] for p in size_score_pairs]
            exec_scores = [p[1] for p in size_score_pairs]
            n = len(sizes)
            mean_size = sum(sizes) / n
            mean_score = sum(exec_scores) / n
            numerator = sum((s - mean_size) * (e - mean_score) for s, e in zip(sizes, exec_scores))
            denom_size = sum((s - mean_size) ** 2 for s in sizes) ** 0.5
            denom_score = sum((e - mean_score) ** 2 for e in exec_scores) ** 0.5
            if denom_size > 0 and denom_score > 0:
                correlation = numerator / (denom_size * denom_score)

        return {
            "trades": matched_trades,
            "summary": {
                "total_trades": len(trades_rows),
                "matched_trades": matched_count,
                "avg_execution_score": round(sum(scores) / matched_count, 4) if matched_count else 0,
                "pct_at_bid": round(at_bid / matched_count * 100, 1) if matched_count else 0,
                "pct_at_ask": round(at_ask / matched_count * 100, 1) if matched_count else 0,
                "pct_mid": round(mid_range / matched_count * 100, 1) if matched_count else 0,
                "maker_avg_score": round(sum(maker_scores) / len(maker_scores), 4) if maker_scores else 0,
                "taker_avg_score": round(sum(taker_scores) / len(taker_scores), 4) if taker_scores else 0
            },
            "distribution": distribution,
            "time_analysis": {
                "by_minute": by_minute,
                "early_avg": round(early_avg, 4),
                "late_avg": round(late_avg, 4),
                "degradation_pct": round(degradation_pct, 1)
            },
            "slippage": {
                "total_usd": round(slippage_total, 2),
                "by_role": {
                    "maker": round(slippage_maker, 2),
                    "taker": round(slippage_taker, 2)
                },
                "by_outcome": {
                    "up": round(slippage_up, 2),
                    "down": round(slippage_down, 2)
                },
                "by_side": {
                    "buy": round(slippage_buy, 2),
                    "sell": round(slippage_sell, 2)
                },
                "avg_per_trade": round(slippage_total / matched_count, 2) if matched_count else 0
            },
            "size_analysis": {
                "correlation": round(correlation, 4),
                "by_bucket": {
                    "small": round(sum(small_scores) / len(small_scores), 4) if small_scores else 0,
                    "medium": round(sum(medium_scores) / len(medium_scores), 4) if medium_scores else 0,
                    "large": round(sum(large_scores) / len(large_scores), 4) if large_scores else 0
                }
            },
            "breakdown": {
                "buy_up": round(sum(breakdown_scores["buy_up"]) / len(breakdown_scores["buy_up"]), 4) if breakdown_scores["buy_up"] else 0,
                "buy_down": round(sum(breakdown_scores["buy_down"]) / len(breakdown_scores["buy_down"]), 4) if breakdown_scores["buy_down"] else 0,
                "sell_up": round(sum(breakdown_scores["sell_up"]) / len(breakdown_scores["sell_up"]), 4) if breakdown_scores["sell_up"] else 0,
                "sell_down": round(sum(breakdown_scores["sell_down"]) / len(breakdown_scores["sell_down"]), 4) if breakdown_scores["sell_down"] else 0
            }
        }

    def get_market_price_trade_overlay(self, market_slug: str) -> Dict:
        """Get price evolution and trade markers for a specific market."""
        with self._get_conn() as conn:
            # Get market info
            market = conn.execute(
                "SELECT * FROM markets WHERE slug = ?", (market_slug,)
            ).fetchone()

            if not market:
                return {
                    "prices": [], "trades": [], "market": None,
                    "spread_analysis": {"by_timestamp": [], "avg_spread": 0, "min_spread": 0, "max_spread": 0},
                    "efficiency": {"by_timestamp": [], "avg_combined": 0, "arbitrage_seconds": 0},
                    "volatility": {"by_minute": [], "vol_trade_correlation": 0},
                    "trade_impact": {"buy_up_impact": 0, "sell_up_impact": 0, "buy_down_impact": 0, "sell_down_impact": 0}
                }

            market_dict = dict(market)

            # Get price snapshots for this market
            prices_rows = conn.execute("""
                SELECT timestamp, outcome, price, best_bid, best_ask
                FROM prices
                WHERE market_slug = ?
                ORDER BY timestamp ASC
            """, (market_slug,)).fetchall()

            # Get trades for this market
            trades_rows = conn.execute("""
                SELECT id, timestamp, side, outcome, role, shares, price, usdc
                FROM trades
                WHERE market_slug = ?
                ORDER BY timestamp ASC
            """, (market_slug,)).fetchall()

        # Convert prices to timeline format (combine UP and DOWN at each timestamp)
        price_timeline = {}
        for row in prices_rows:
            r = dict(row)
            ts = r["timestamp"]
            if ts not in price_timeline:
                price_timeline[ts] = {
                    "timestamp": ts,
                    "timestamp_iso": datetime.utcfromtimestamp(ts).isoformat() + "Z",
                    "up_price": None, "up_bid": None, "up_ask": None,
                    "down_price": None, "down_bid": None, "down_ask": None
                }
            if r["outcome"] == "Up":
                price_timeline[ts]["up_price"] = r["price"]
                price_timeline[ts]["up_bid"] = r["best_bid"]
                price_timeline[ts]["up_ask"] = r["best_ask"]
            else:
                price_timeline[ts]["down_price"] = r["price"]
                price_timeline[ts]["down_bid"] = r["best_bid"]
                price_timeline[ts]["down_ask"] = r["best_ask"]

        prices = sorted(price_timeline.values(), key=lambda x: x["timestamp"])

        # Convert trades
        trades = [{
            "id": r["id"],
            "timestamp": r["timestamp"],
            "timestamp_iso": datetime.utcfromtimestamp(r["timestamp"]).isoformat() + "Z",
            "side": r["side"],
            "outcome": r["outcome"],
            "role": r["role"],
            "shares": r["shares"],
            "price": r["price"],
            "usdc": r["usdc"]
        } for r in trades_rows]

        # For 15-minute markets, calculate correct start_time (end_time - 15 min)
        # The API's startDate is market creation, not the 15-min window start
        end_time = market_dict["end_time"]
        if end_time and "15m" in market_dict["slug"]:
            calculated_start = end_time - 900  # 15 minutes = 900 seconds
        else:
            calculated_start = market_dict["start_time"]

        # NEW: Calculate spread analysis
        spread_data = []
        spreads = []
        for p in prices:
            up_spread = (p["up_ask"] - p["up_bid"]) if p["up_ask"] and p["up_bid"] else None
            down_spread = (p["down_ask"] - p["down_bid"]) if p["down_ask"] and p["down_bid"] else None
            spread_data.append({
                "timestamp": p["timestamp"],
                "up_spread": round(up_spread, 4) if up_spread else None,
                "down_spread": round(down_spread, 4) if down_spread else None
            })
            if up_spread is not None:
                spreads.append(up_spread)
            if down_spread is not None:
                spreads.append(down_spread)

        # NEW: Calculate market efficiency (combined price = up + down should equal 1.0)
        efficiency_data = []
        combined_prices = []
        arbitrage_seconds = 0
        for p in prices:
            if p["up_price"] is not None and p["down_price"] is not None:
                combined = p["up_price"] + p["down_price"]
                efficiency_data.append({
                    "timestamp": p["timestamp"],
                    "combined": round(combined, 4)
                })
                combined_prices.append(combined)
                if combined < 0.98:
                    arbitrage_seconds += 1  # Each price point is ~1 second

        # NEW: Calculate volatility by minute
        if calculated_start:
            minute_prices = {}  # {minute: [prices]}
            minute_trade_counts = {}  # {minute: count}

            for p in prices:
                minute = int((p["timestamp"] - calculated_start) / 60)
                minute = max(0, min(14, minute))
                if minute not in minute_prices:
                    minute_prices[minute] = []
                if p["up_price"] is not None:
                    minute_prices[minute].append(p["up_price"])
                if p["down_price"] is not None:
                    minute_prices[minute].append(p["down_price"])

            for t in trades:
                minute = int((t["timestamp"] - calculated_start) / 60)
                minute = max(0, min(14, minute))
                minute_trade_counts[minute] = minute_trade_counts.get(minute, 0) + 1

            volatility_data = []
            vol_values = []
            trade_counts = []
            for minute in range(15):
                prices_in_minute = minute_prices.get(minute, [])
                trade_count = minute_trade_counts.get(minute, 0)

                # Calculate volatility as standard deviation
                if len(prices_in_minute) > 1:
                    mean_price = sum(prices_in_minute) / len(prices_in_minute)
                    variance = sum((p - mean_price) ** 2 for p in prices_in_minute) / len(prices_in_minute)
                    volatility = variance ** 0.5
                else:
                    volatility = 0

                volatility_data.append({
                    "minute": minute,
                    "volatility": round(volatility, 6),
                    "trade_count": trade_count
                })
                vol_values.append(volatility)
                trade_counts.append(trade_count)

            # Calculate correlation between volatility and trade count
            vol_trade_correlation = 0
            if len(vol_values) > 1 and sum(vol_values) > 0 and sum(trade_counts) > 0:
                n = len(vol_values)
                mean_vol = sum(vol_values) / n
                mean_tc = sum(trade_counts) / n
                numerator = sum((v - mean_vol) * (tc - mean_tc) for v, tc in zip(vol_values, trade_counts))
                denom_vol = sum((v - mean_vol) ** 2 for v in vol_values) ** 0.5
                denom_tc = sum((tc - mean_tc) ** 2 for tc in trade_counts) ** 0.5
                if denom_vol > 0 and denom_tc > 0:
                    vol_trade_correlation = numerator / (denom_vol * denom_tc)
        else:
            volatility_data = []
            vol_trade_correlation = 0

        # NEW: Calculate trade impact (price change after trade)
        # Build price lookup by timestamp for quick access
        price_lookup = {p["timestamp"]: p for p in prices}

        trade_impacts = {"buy_up": [], "sell_up": [], "buy_down": [], "sell_down": []}
        for t in trades:
            trade_ts = t["timestamp"]
            outcome = t["outcome"]
            side = t["side"]

            # Find price 30 seconds after trade
            future_ts = trade_ts + 30
            closest_future = None
            min_diff = float('inf')
            for ts, p in price_lookup.items():
                if ts >= future_ts and ts - future_ts < min_diff:
                    min_diff = ts - future_ts
                    closest_future = p

            if closest_future and min_diff <= 60:  # Within 60 seconds after target
                # Get price at trade time (closest)
                closest_current = None
                min_current_diff = float('inf')
                for ts, p in price_lookup.items():
                    diff = abs(ts - trade_ts)
                    if diff < min_current_diff:
                        min_current_diff = diff
                        closest_current = p

                if closest_current and min_current_diff <= 30:
                    if outcome == "Up":
                        price_at_trade = closest_current.get("up_price")
                        price_after = closest_future.get("up_price")
                    else:
                        price_at_trade = closest_current.get("down_price")
                        price_after = closest_future.get("down_price")

                    if price_at_trade and price_after:
                        impact = price_after - price_at_trade
                        key = f"{side.lower()}_{outcome.lower()}"
                        trade_impacts[key].append(impact)

        # NEW: Downsample prices to 1 per 5 seconds for cleaner chart
        prices_downsampled = []
        if prices:
            bucket_size = 5  # 5 seconds per point
            current_bucket = None
            bucket_data = None

            for p in prices:
                bucket = (p["timestamp"] // bucket_size) * bucket_size
                if bucket != current_bucket:
                    if bucket_data:
                        prices_downsampled.append(bucket_data)
                    current_bucket = bucket
                    bucket_data = p.copy()
                else:
                    # Update with latest values in bucket
                    for key in ["up_price", "up_bid", "up_ask", "down_price", "down_bid", "down_ask"]:
                        if p[key] is not None:
                            bucket_data[key] = p[key]
            if bucket_data:
                prices_downsampled.append(bucket_data)

        # NEW: Aggregate trades by minute for volume bars
        trade_volume_by_minute = []
        if calculated_start and trades:
            minute_volumes = {}  # {minute: {buy_up, sell_up, buy_down, sell_down, buy_up_shares, sell_up_shares, ...}}

            for t in trades:
                minute = int((t["timestamp"] - calculated_start) / 60)
                minute = max(0, min(14, minute))  # Clamp to 0-14 for 15-min markets

                if minute not in minute_volumes:
                    minute_volumes[minute] = {
                        "minute": minute,
                        "buy_up_usdc": 0, "sell_up_usdc": 0,
                        "buy_down_usdc": 0, "sell_down_usdc": 0,
                        "buy_up_shares": 0, "sell_up_shares": 0,
                        "buy_down_shares": 0, "sell_down_shares": 0,
                        "trade_count": 0
                    }

                key_prefix = f"{t['side'].lower()}_{t['outcome'].lower()}"
                minute_volumes[minute][f"{key_prefix}_usdc"] += t["usdc"]
                minute_volumes[minute][f"{key_prefix}_shares"] += t["shares"]
                minute_volumes[minute]["trade_count"] += 1

            # Convert to sorted list
            for minute in range(15):
                if minute in minute_volumes:
                    trade_volume_by_minute.append(minute_volumes[minute])
                else:
                    trade_volume_by_minute.append({
                        "minute": minute,
                        "buy_up_usdc": 0, "sell_up_usdc": 0,
                        "buy_down_usdc": 0, "sell_down_usdc": 0,
                        "buy_up_shares": 0, "sell_up_shares": 0,
                        "buy_down_shares": 0, "sell_down_shares": 0,
                        "trade_count": 0
                    })

        return {
            "prices": prices,
            "prices_downsampled": prices_downsampled,
            "trades": trades,
            "trade_volume_by_minute": trade_volume_by_minute,
            "market": {
                "slug": market_dict["slug"],
                "question": market_dict["question"] or "",
                "start_time": calculated_start,
                "end_time": end_time,
                "winning_outcome": market_dict["winning_outcome"]
            },
            "spread_analysis": {
                "by_timestamp": spread_data,
                "avg_spread": round(sum(spreads) / len(spreads), 4) if spreads else 0,
                "min_spread": round(min(spreads), 4) if spreads else 0,
                "max_spread": round(max(spreads), 4) if spreads else 0
            },
            "efficiency": {
                "by_timestamp": efficiency_data,
                "avg_combined": round(sum(combined_prices) / len(combined_prices), 4) if combined_prices else 0,
                "arbitrage_seconds": arbitrage_seconds
            },
            "volatility": {
                "by_minute": volatility_data,
                "vol_trade_correlation": round(vol_trade_correlation, 4)
            },
            "trade_impact": {
                "buy_up_impact": round(sum(trade_impacts["buy_up"]) / len(trade_impacts["buy_up"]) * 100, 2) if trade_impacts["buy_up"] else 0,
                "sell_up_impact": round(sum(trade_impacts["sell_up"]) / len(trade_impacts["sell_up"]) * 100, 2) if trade_impacts["sell_up"] else 0,
                "buy_down_impact": round(sum(trade_impacts["buy_down"]) / len(trade_impacts["buy_down"]) * 100, 2) if trade_impacts["buy_down"] else 0,
                "sell_down_impact": round(sum(trade_impacts["sell_down"]) / len(trade_impacts["sell_down"]) * 100, 2) if trade_impacts["sell_down"] else 0
            }
        }

    def get_position_evolution(self, market_slug: str) -> Dict:
        """Get position building over time for a market with enhanced metrics."""
        with self._get_conn() as conn:
            # Get trades with price data for entry quality analysis
            rows = conn.execute("""
                SELECT t.id, t.timestamp, t.side, t.outcome, t.shares, t.price, t.usdc,
                       p.price as mid_price, p.best_bid, p.best_ask
                FROM trades t
                LEFT JOIN prices p ON t.market_slug = p.market_slug
                    AND t.outcome = p.outcome
                    AND p.timestamp = (
                        SELECT MAX(p2.timestamp) FROM prices p2
                        WHERE p2.market_slug = t.market_slug
                        AND p2.outcome = t.outcome
                        AND p2.timestamp <= t.timestamp
                    )
                WHERE t.market_slug = ?
                ORDER BY t.timestamp ASC
            """, (market_slug,)).fetchall()

            # Get market info for final P&L calculation
            market_info = conn.execute("""
                SELECT winning_outcome, resolved FROM markets WHERE slug = ?
            """, (market_slug,)).fetchone()

        winning_outcome = market_info["winning_outcome"] if market_info else None
        is_resolved = market_info["resolved"] if market_info else False

        evolution = []
        up_shares = 0
        down_shares = 0
        total_cost = 0
        total_revenue = 0

        # Cost basis tracking (VWAP)
        up_total_cost = 0  # Total $ spent on UP
        down_total_cost = 0  # Total $ spent on DOWN
        up_shares_bought = 0  # Total UP shares bought (for VWAP)
        down_shares_bought = 0  # Total DOWN shares bought (for VWAP)

        # P&L tracking
        realized_pnl = 0

        # Entry quality tracking
        entry_edges = []  # List of (edge_cents, shares) for each buy

        # Position sizing tracking
        buy_sizes = []  # List of share sizes for each buy

        for row in rows:
            r = dict(row)
            trade_price = r["price"]
            mid_price = r["mid_price"] if r["mid_price"] else trade_price
            shares = r["shares"]
            usdc = r["usdc"]

            # Calculate entry edge (how much better than mid)
            # For BUY: lower is better, so edge = mid - trade_price
            # For SELL: higher is better, so edge = trade_price - mid
            if r["side"] == "BUY":
                entry_edge = (mid_price - trade_price) * 100  # In cents
                entry_edges.append((entry_edge, shares))
                buy_sizes.append(shares)

                if r["outcome"] == "Up":
                    up_shares += shares
                    up_total_cost += usdc
                    up_shares_bought += shares
                else:
                    down_shares += shares
                    down_total_cost += usdc
                    down_shares_bought += shares
                total_cost += usdc
            else:  # SELL
                entry_edge = (trade_price - mid_price) * 100  # In cents
                entry_edges.append((entry_edge, shares))

                # Calculate realized P&L on sell
                if r["outcome"] == "Up" and up_shares_bought > 0:
                    avg_cost = up_total_cost / up_shares_bought
                    realized_pnl += (trade_price - avg_cost) * shares
                    up_shares -= shares
                elif r["outcome"] == "Down" and down_shares_bought > 0:
                    avg_cost = down_total_cost / down_shares_bought
                    realized_pnl += (trade_price - avg_cost) * shares
                    down_shares -= shares
                total_revenue += usdc

            # Calculate current VWAP for each side
            up_avg_cost = up_total_cost / up_shares_bought if up_shares_bought > 0 else 0
            down_avg_cost = down_total_cost / down_shares_bought if down_shares_bought > 0 else 0
            combined_cost = up_avg_cost + down_avg_cost

            # Calculate unrealized P&L (mark-to-market using current mid)
            unrealized_pnl = 0
            if up_shares > 0 and up_avg_cost > 0:
                # UP position value at current mid
                current_up_mid = mid_price if r["outcome"] == "Up" else (1 - mid_price)
                unrealized_pnl += (current_up_mid - up_avg_cost) * up_shares
            if down_shares > 0 and down_avg_cost > 0:
                # DOWN position value at current mid
                current_down_mid = mid_price if r["outcome"] == "Down" else (1 - mid_price)
                unrealized_pnl += (current_down_mid - down_avg_cost) * down_shares

            # Calculate hedge ratio
            if up_shares > 0 and down_shares > 0:
                hedge_ratio = min(up_shares, down_shares) / max(up_shares, down_shares)
            elif up_shares > 0 or down_shares > 0:
                hedge_ratio = 0
            else:
                hedge_ratio = 1.0

            evolution.append({
                "timestamp": r["timestamp"],
                "timestamp_iso": datetime.utcfromtimestamp(r["timestamp"]).isoformat() + "Z",
                "up_shares": round(max(0, up_shares), 2),
                "down_shares": round(max(0, down_shares), 2),
                "net_position": round(up_shares - down_shares, 2),
                "hedge_ratio": round(hedge_ratio * 100, 1),
                "total_cost": round(total_cost, 2),
                "total_revenue": round(total_revenue, 2),
                # NEW: Cost basis fields
                "up_avg_cost": round(up_avg_cost, 4),
                "down_avg_cost": round(down_avg_cost, 4),
                "combined_cost": round(combined_cost, 4),
                # NEW: P&L fields
                "realized_pnl": round(realized_pnl, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "total_pnl": round(realized_pnl + unrealized_pnl, 2),
                # NEW: Entry quality for this trade
                "entry_edge": round(entry_edge, 2)
            })

        # Calculate summary statistics
        total_edge_value = sum(edge * shares for edge, shares in entry_edges) / 100 if entry_edges else 0
        avg_entry_edge = sum(edge for edge, _ in entry_edges) / len(entry_edges) if entry_edges else 0
        pct_positive_edge = len([e for e, _ in entry_edges if e > 0]) / len(entry_edges) * 100 if entry_edges else 0

        # Position sizing stats
        if buy_sizes:
            avg_size = sum(buy_sizes) / len(buy_sizes)
            if len(buy_sizes) > 1:
                variance = sum((s - avg_size) ** 2 for s in buy_sizes) / (len(buy_sizes) - 1)
                stddev = variance ** 0.5
            else:
                stddev = 0
            coefficient_variation = stddev / avg_size if avg_size > 0 else 0
            largest_pct = max(buy_sizes) / sum(buy_sizes) * 100 if sum(buy_sizes) > 0 else 0
        else:
            avg_size = 0
            stddev = 0
            coefficient_variation = 0
            largest_pct = 0

        # Final P&L calculation if market resolved
        final_pnl = None
        if is_resolved and winning_outcome:
            # Winning side pays $1, losing side pays $0
            if winning_outcome == "Up":
                final_pnl = up_shares * 1.0 + down_shares * 0.0 - total_cost + total_revenue
            else:
                final_pnl = up_shares * 0.0 + down_shares * 1.0 - total_cost + total_revenue

        # NEW: Calculate position vs price correlation
        with self._get_conn() as conn:
            # Get price data for correlation analysis
            prices_rows = conn.execute("""
                SELECT timestamp, outcome, price as mid_price
                FROM prices
                WHERE market_slug = ?
                ORDER BY timestamp ASC
            """, (market_slug,)).fetchall()

            # Also get buy trades with prices for "bought the dip" analysis
            buy_trades = conn.execute("""
                SELECT t.timestamp, t.outcome, t.price as trade_price, t.shares
                FROM trades t
                WHERE t.market_slug = ? AND t.side = 'BUY'
                ORDER BY t.timestamp ASC
            """, (market_slug,)).fetchall()

            # Get sell trades for "sold the top" analysis
            sell_trades = conn.execute("""
                SELECT t.timestamp, t.outcome, t.price as trade_price, t.shares
                FROM trades t
                WHERE t.market_slug = ? AND t.side = 'SELL'
                ORDER BY t.timestamp ASC
            """, (market_slug,)).fetchall()

        # Build price lookup by timestamp and outcome
        up_prices = {}
        down_prices = {}
        for pr in prices_rows:
            p = dict(pr)
            if p["outcome"] == "Up":
                up_prices[p["timestamp"]] = p["mid_price"]
            else:
                down_prices[p["timestamp"]] = p["mid_price"]

        # Calculate average prices for "bought below" analysis
        avg_up_price = sum(up_prices.values()) / len(up_prices) if up_prices else 0.5
        avg_down_price = sum(down_prices.values()) / len(down_prices) if down_prices else 0.5

        # Calculate "bought the dip" percentages
        up_buys_below_avg = 0
        up_buy_total = 0
        down_buys_below_avg = 0
        down_buy_total = 0
        for bt in buy_trades:
            b = dict(bt)
            if b["outcome"] == "Up":
                up_buy_total += 1
                if b["trade_price"] < avg_up_price:
                    up_buys_below_avg += 1
            else:
                down_buy_total += 1
                if b["trade_price"] < avg_down_price:
                    down_buys_below_avg += 1

        # Calculate "sold the top" percentages
        up_sells_above_avg = 0
        up_sell_total = 0
        down_sells_above_avg = 0
        down_sell_total = 0
        for st in sell_trades:
            s = dict(st)
            if s["outcome"] == "Up":
                up_sell_total += 1
                if s["trade_price"] > avg_up_price:
                    up_sells_above_avg += 1
            else:
                down_sell_total += 1
                if s["trade_price"] > avg_down_price:
                    down_sells_above_avg += 1

        # Build timeline for position vs price correlation charts
        # Sample prices at ~10 second intervals and track cumulative position
        price_position_timeline = []
        up_pos = 0
        down_pos = 0
        trade_idx = 0
        sorted_rows = sorted([dict(r) for r in rows], key=lambda x: x["timestamp"])

        # Get unique price timestamps
        all_timestamps = sorted(set(list(up_prices.keys()) + list(down_prices.keys())))

        for ts in all_timestamps[::5]:  # Sample every 5th price point (~5 seconds)
            # Update position based on trades up to this timestamp
            while trade_idx < len(sorted_rows) and sorted_rows[trade_idx]["timestamp"] <= ts:
                t = sorted_rows[trade_idx]
                if t["side"] == "BUY":
                    if t["outcome"] == "Up":
                        up_pos += t["shares"]
                    else:
                        down_pos += t["shares"]
                else:
                    if t["outcome"] == "Up":
                        up_pos = max(0, up_pos - t["shares"])
                    else:
                        down_pos = max(0, down_pos - t["shares"])
                trade_idx += 1

            up_price = up_prices.get(ts)
            down_price = down_prices.get(ts)

            # Find closest price if exact timestamp not found
            if up_price is None:
                closest_ts = min(up_prices.keys(), key=lambda x: abs(x - ts), default=None)
                up_price = up_prices.get(closest_ts) if closest_ts else None
            if down_price is None:
                closest_ts = min(down_prices.keys(), key=lambda x: abs(x - ts), default=None)
                down_price = down_prices.get(closest_ts) if closest_ts else None

            price_position_timeline.append({
                "timestamp": ts,
                "timestamp_iso": datetime.utcfromtimestamp(ts).isoformat() + "Z",
                "up_shares": round(up_pos, 2),
                "down_shares": round(down_pos, 2),
                "up_price": round(up_price, 4) if up_price else None,
                "down_price": round(down_price, 4) if down_price else None
            })

        # Calculate Pearson correlation between position and price
        def calc_correlation(positions, prices):
            """Calculate Pearson correlation coefficient."""
            if len(positions) < 3 or len(prices) < 3:
                return 0
            # Filter out None values
            valid_pairs = [(p, pr) for p, pr in zip(positions, prices) if p is not None and pr is not None]
            if len(valid_pairs) < 3:
                return 0
            positions = [p for p, _ in valid_pairs]
            prices = [pr for _, pr in valid_pairs]

            n = len(positions)
            mean_pos = sum(positions) / n
            mean_price = sum(prices) / n

            # Check for zero variance
            var_pos = sum((p - mean_pos) ** 2 for p in positions)
            var_price = sum((pr - mean_price) ** 2 for pr in prices)
            if var_pos == 0 or var_price == 0:
                return 0

            numerator = sum((p - mean_pos) * (pr - mean_price) for p, pr in zip(positions, prices))
            denominator = (var_pos ** 0.5) * (var_price ** 0.5)
            return numerator / denominator if denominator > 0 else 0

        up_positions = [p["up_shares"] for p in price_position_timeline]
        down_positions = [p["down_shares"] for p in price_position_timeline]
        up_price_vals = [p["up_price"] for p in price_position_timeline]
        down_price_vals = [p["down_price"] for p in price_position_timeline]

        up_corr = calc_correlation(up_positions, up_price_vals)
        down_corr = calc_correlation(down_positions, down_price_vals)

        price_correlation = {
            "up_shares_vs_up_price": round(up_corr, 3),
            "down_shares_vs_down_price": round(down_corr, 3),
            "pct_bought_below_avg_up": round(up_buys_below_avg / up_buy_total * 100, 1) if up_buy_total > 0 else 0,
            "pct_bought_below_avg_down": round(down_buys_below_avg / down_buy_total * 100, 1) if down_buy_total > 0 else 0,
            "pct_sold_above_avg_up": round(up_sells_above_avg / up_sell_total * 100, 1) if up_sell_total > 0 else 0,
            "pct_sold_above_avg_down": round(down_sells_above_avg / down_sell_total * 100, 1) if down_sell_total > 0 else 0,
            "avg_up_price": round(avg_up_price, 4),
            "avg_down_price": round(avg_down_price, 4),
            "timeline": price_position_timeline
        }

        return {
            "points": evolution,
            "summary": {
                "final_up_shares": round(max(0, up_shares), 2),
                "final_down_shares": round(max(0, down_shares), 2),
                "final_up_vwap": round(up_total_cost / up_shares_bought, 4) if up_shares_bought > 0 else 0,
                "final_down_vwap": round(down_total_cost / down_shares_bought, 4) if down_shares_bought > 0 else 0,
                "final_combined_cost": round(
                    (up_total_cost / up_shares_bought if up_shares_bought > 0 else 0) +
                    (down_total_cost / down_shares_bought if down_shares_bought > 0 else 0), 4
                ),
                "total_cost": round(total_cost, 2),
                "total_revenue": round(total_revenue, 2),
                "total_realized_pnl": round(realized_pnl, 2),
                "final_pnl": round(final_pnl, 2) if final_pnl is not None else None,
                "winning_outcome": winning_outcome
            },
            "entry_quality": {
                "avg_entry_edge": round(avg_entry_edge, 2),  # Cents better than mid
                "pct_positive_edge": round(pct_positive_edge, 1),  # % of trades with positive edge
                "total_edge_value": round(total_edge_value, 2),  # Total $ saved from good entries
                "trade_count": len(entry_edges)
            },
            "sizing": {
                "buy_sizes": [round(s, 2) for s in buy_sizes],
                "buy_count": len(buy_sizes),
                "avg_size": round(avg_size, 2),
                "stddev": round(stddev, 2),
                "coefficient_variation": round(coefficient_variation, 3),  # Low = DCA, High = variable
                "largest_pct": round(largest_pct, 1),
                "pattern": "DCA" if coefficient_variation < 0.3 else ("Variable" if coefficient_variation < 0.7 else "Concentrated")
            },
            "price_correlation": price_correlation
        }

    def get_trading_intensity_patterns(self) -> Dict:
        """Analyze when trades occur within markets (relative timing)."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT
                    t.timestamp as trade_ts,
                    t.market_slug,
                    t.shares,
                    t.usdc,
                    m.start_time,
                    m.end_time,
                    m.winning_outcome
                FROM trades t
                JOIN markets m ON t.market_slug = m.slug
                WHERE m.resolved = 1 AND m.start_time IS NOT NULL AND m.end_time IS NOT NULL
            """).fetchall()

        if not rows:
            return {
                "by_minute": [],
                "by_phase": {"early": 0, "middle": 0, "late": 0},
                "total_trades": 0
            }

        # Group trades by minute within market (0-15 for 15-min markets)
        minute_counts = {}
        phase_counts = {"early": 0, "middle": 0, "late": 0}

        for row in rows:
            r = dict(row)
            # For 15m markets, use calculated start (end - 15 min) instead of DB start_time
            if "15m" in r["market_slug"]:
                actual_start = r["end_time"] - 900
                market_duration = 900
            else:
                actual_start = r["start_time"]
                market_duration = r["end_time"] - r["start_time"]

            if market_duration <= 0:
                continue

            time_into_market = r["trade_ts"] - actual_start
            minute = int(time_into_market / 60)
            minute = max(0, min(14, minute))  # Clamp to 0-14

            if minute not in minute_counts:
                minute_counts[minute] = {"count": 0, "volume": 0}
            minute_counts[minute]["count"] += 1
            minute_counts[minute]["volume"] += r["usdc"]

            # Phase analysis (use already calculated time_into_market and market_duration)
            if market_duration > 0:
                pct_into_market = time_into_market / market_duration
            else:
                pct_into_market = 0.5
            if pct_into_market < 0.33:
                phase_counts["early"] += 1
            elif pct_into_market < 0.67:
                phase_counts["middle"] += 1
            else:
                phase_counts["late"] += 1

        # Build minute breakdown
        by_minute = []
        for minute in range(15):
            data = minute_counts.get(minute, {"count": 0, "volume": 0})
            by_minute.append({
                "minute": minute,
                "trade_count": data["count"],
                "volume": round(data["volume"], 2)
            })

        return {
            "by_minute": by_minute,
            "by_phase": phase_counts,
            "total_trades": len(rows)
        }

    def get_loss_pattern_analysis(self) -> Dict:
        """Compare winning vs losing markets across multiple dimensions."""
        markets = self.get_markets_analytics()

        if not markets:
            return {
                "winners": {"count": 0, "metrics": {}},
                "losers": {"count": 0, "metrics": {}},
                "comparison": []
            }

        winners = [m for m in markets if m["pnl"] > 0]
        losers = [m for m in markets if m["pnl"] < 0]

        def calc_metrics(market_list: List[Dict]) -> Dict:
            if not market_list:
                return {
                    "avg_hedge_ratio": 0,
                    "avg_maker_ratio": 0,
                    "avg_combined_price": 0,
                    "avg_trades": 0,
                    "avg_volume": 0,
                    "avg_edge": 0,
                    "pct_correct_bias": 0,
                    "pct_balanced": 0,
                    "avg_pnl": 0
                }

            n = len(market_list)
            return {
                "avg_hedge_ratio": round(sum(m["hedge_ratio"] for m in market_list) / n, 1),
                "avg_maker_ratio": round(sum(m["maker_ratio"] for m in market_list) / n, 1),
                "avg_combined_price": round(sum(m["combined_price"] for m in market_list) / n, 4),
                "avg_trades": round(sum(m["trades"] for m in market_list) / n, 1),
                "avg_volume": round(sum(m["volume"] for m in market_list) / n, 2),
                "avg_edge": round(sum(m["edge"] for m in market_list) / n, 2),
                "pct_correct_bias": round(len([m for m in market_list if m["correct_bias"]]) / n * 100, 1),
                "pct_balanced": round(len([m for m in market_list if m["net_bias"] == "BALANCED"]) / n * 100, 1),
                "avg_pnl": round(sum(m["pnl"] for m in market_list) / n, 2)
            }

        winner_metrics = calc_metrics(winners)
        loser_metrics = calc_metrics(losers)

        # Build comparison table
        metrics = ["avg_hedge_ratio", "avg_maker_ratio", "avg_combined_price", "avg_trades",
                   "avg_volume", "avg_edge", "pct_correct_bias", "pct_balanced"]
        comparison = []
        for metric in metrics:
            w_val = winner_metrics[metric]
            l_val = loser_metrics[metric]
            diff = w_val - l_val if isinstance(w_val, (int, float)) and isinstance(l_val, (int, float)) else None
            comparison.append({
                "metric": metric,
                "winners": w_val,
                "losers": l_val,
                "difference": round(diff, 2) if diff is not None else None
            })

        # Box plot data - distributions for key metrics
        def get_distribution(market_list: List[Dict], key: str) -> Dict:
            values = [m[key] for m in market_list if m[key] is not None]
            if not values:
                return {"min": 0, "q1": 0, "median": 0, "q3": 0, "max": 0}
            values.sort()
            n = len(values)
            return {
                "min": round(values[0], 2),
                "q1": round(values[n // 4], 2),
                "median": round(values[n // 2], 2),
                "q3": round(values[3 * n // 4], 2),
                "max": round(values[-1], 2)
            }

        distributions = {}
        for key in ["hedge_ratio", "maker_ratio", "combined_price", "edge"]:
            distributions[key] = {
                "winners": get_distribution(winners, key),
                "losers": get_distribution(losers, key)
            }

        return {
            "winners": {"count": len(winners), "metrics": winner_metrics},
            "losers": {"count": len(losers), "metrics": loser_metrics},
            "comparison": comparison,
            "distributions": distributions,
            "all_markets": markets  # For detailed analysis
        }

    def get_risk_metrics(self) -> Dict:
        """Calculate risk-adjusted performance metrics."""
        markets = self.get_markets_analytics()

        if not markets:
            return {
                "sharpe": 0,
                "max_drawdown": 0,
                "calmar": 0,
                "var_5pct": 0,
                "win_streak": 0,
                "loss_streak": 0,
                "current_streak": 0,
                "win_rate": 0,
                "win_rate_ci_low": 0,
                "win_rate_ci_high": 0,
                "total_pnl": 0,
                "total_markets": 0,
                "pnl_std": 0,
                "mean_pnl": 0
            }

        pnls = [m["pnl"] for m in markets]
        n = len(pnls)

        # Basic stats
        total_pnl = sum(pnls)
        mean_pnl = total_pnl / n
        variance = sum((p - mean_pnl) ** 2 for p in pnls) / n
        std_pnl = variance ** 0.5 if variance > 0 else 0

        # Sharpe-like ratio (mean / std)
        sharpe = mean_pnl / std_pnl if std_pnl > 0 else 0

        # Calculate cumulative P&L for drawdown
        cumulative = []
        running = 0
        for pnl in pnls:
            running += pnl
            cumulative.append(running)

        # Max drawdown
        peak = cumulative[0]
        max_drawdown = 0
        for val in cumulative:
            if val > peak:
                peak = val
            drawdown = peak - val
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Calmar ratio (total P&L / max drawdown)
        calmar = total_pnl / max_drawdown if max_drawdown > 0 else float('inf') if total_pnl > 0 else 0

        # VaR 5% (5th percentile P&L)
        sorted_pnls = sorted(pnls)
        var_idx = int(n * 0.05)
        var_5pct = sorted_pnls[var_idx] if var_idx < n else sorted_pnls[0]

        # Streaks
        win_streak = 0
        loss_streak = 0
        current_streak = 0
        current_type = None
        max_win_streak = 0
        max_loss_streak = 0

        for pnl in pnls:
            if pnl > 0:
                if current_type == "win":
                    current_streak += 1
                else:
                    current_streak = 1
                    current_type = "win"
                max_win_streak = max(max_win_streak, current_streak)
            else:
                if current_type == "loss":
                    current_streak += 1
                else:
                    current_streak = 1
                    current_type = "loss"
                max_loss_streak = max(max_loss_streak, current_streak)

        # Win rate with 95% confidence interval (binomial)
        wins = len([p for p in pnls if p > 0])
        win_rate = wins / n if n > 0 else 0

        # Wilson score interval for binomial proportion
        z = 1.96  # 95% CI
        denominator = 1 + z * z / n
        center = (win_rate + z * z / (2 * n)) / denominator
        spread = z * ((win_rate * (1 - win_rate) + z * z / (4 * n)) / n) ** 0.5 / denominator

        win_rate_ci_low = max(0, center - spread)
        win_rate_ci_high = min(1, center + spread)

        return {
            "sharpe": round(sharpe, 3),
            "max_drawdown": round(max_drawdown, 2),
            "calmar": round(calmar, 2) if calmar != float('inf') else 999,
            "var_5pct": round(var_5pct, 2),
            "win_streak": max_win_streak,
            "loss_streak": max_loss_streak,
            "current_streak": current_streak,
            "current_streak_type": current_type,
            "win_rate": round(win_rate * 100, 1),
            "win_rate_ci_low": round(win_rate_ci_low * 100, 1),
            "win_rate_ci_high": round(win_rate_ci_high * 100, 1),
            "total_pnl": round(total_pnl, 2),
            "total_markets": n,
            "pnl_std": round(std_pnl, 2),
            "mean_pnl": round(mean_pnl, 2)
        }
