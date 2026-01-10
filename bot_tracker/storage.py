"""
JSON file storage for trades and market data.
Uses consolidated files (all data in single files, not per-session).
"""

import json
import os
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path
from filelock import FileLock

from .models import TradeEvent, WalletPosition, MarketContext


class JSONStorage:
    """Saves tracking data to consolidated JSON files."""

    def __init__(self, db_dir: str = None):
        """
        Initialize storage.

        Args:
            db_dir: Directory to save files. Defaults to DATA_DIR env var or bot_tracker/db/
        """
        if db_dir is None:
            # Use DATA_DIR env var for Railway volumes, fallback to local
            db_dir = os.getenv("DATA_DIR", str(Path(__file__).parent / "db"))

        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)

        # Consolidated file paths
        self.trades_file = self.db_dir / "trades.json"
        self.positions_file = self.db_dir / "positions.json"
        self.markets_file = self.db_dir / "markets.json"
        self.sessions_file = self.db_dir / "sessions.json"
        self.prices_file = self.db_dir / "prices.json"

        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = datetime.now()

        # In-memory cache for current session
        self.session_trades: List[dict] = []
        self.session_trade_ids: set = set()

        # Initialize files if they don't exist
        self._init_files()

        # Record session start
        self._record_session_start()

        print(f"Storage initialized: {self.db_dir}")
        print(f"  Session: {self.session_id}")

    def _init_files(self):
        """Initialize JSON files if they don't exist."""
        if not self.trades_file.exists():
            self._write_json(self.trades_file, [])

        if not self.positions_file.exists():
            self._write_json(self.positions_file, {})

        if not self.markets_file.exists():
            self._write_json(self.markets_file, {})

        if not self.sessions_file.exists():
            self._write_json(self.sessions_file, [])

        if not self.prices_file.exists():
            self._write_json(self.prices_file, [])

    def _read_json(self, filepath: Path):
        """Read JSON file with lock."""
        lock = FileLock(str(filepath) + ".lock")
        with lock:
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return [] if filepath != self.positions_file and filepath != self.markets_file else {}

    def _write_json(self, filepath: Path, data):
        """Write JSON file with lock."""
        lock = FileLock(str(filepath) + ".lock")
        with lock:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

    def _append_json(self, filepath: Path, item: dict):
        """Append item to JSON array file."""
        lock = FileLock(str(filepath) + ".lock")
        with lock:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                data = []

            data.append(item)

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

    def _record_session_start(self):
        """Record new session in sessions file."""
        session = {
            "session_id": self.session_id,
            "started_at": self.session_start.isoformat(),
            "ended_at": None,
            "trades_count": 0
        }
        self._append_json(self.sessions_file, session)

    def save_trade(self, trade: TradeEvent):
        """Save a single trade to consolidated file."""
        # Create unique key to prevent duplicates
        trade_key = f"{trade.tx_hash}:{trade.outcome}:{trade.shares}"

        if trade_key in self.session_trade_ids:
            return  # Skip duplicate

        self.session_trade_ids.add(trade_key)

        trade_dict = {
            "id": trade.id,
            "tx_hash": trade.tx_hash,
            "timestamp": trade.timestamp,
            "timestamp_iso": datetime.fromtimestamp(trade.timestamp).isoformat(),
            "wallet": trade.wallet,
            "wallet_name": trade.wallet_name,
            "role": trade.role,
            "side": trade.side,
            "outcome": trade.outcome,
            "shares": trade.shares,
            "usdc": trade.usdc,
            "price": trade.price,
            "fee": trade.fee,
            "market_slug": trade.market_slug,
            "market_question": trade.market_question,
            "session_id": self.session_id,
            "recorded_at": datetime.now().isoformat()
        }

        self.session_trades.append(trade_dict)
        self._append_json(self.trades_file, trade_dict)

    def save_trades(self, trades: List[TradeEvent]):
        """Save multiple trades."""
        for trade in trades:
            self.save_trade(trade)

    def save_position(self, position: WalletPosition):
        """Save/update position (overwrites existing for same wallet/market)."""
        pos_dict = {
            "wallet": position.wallet,
            "wallet_name": position.wallet_name,
            "market_slug": position.market_slug,
            "up_shares": position.up_shares,
            "down_shares": position.down_shares,
            "up_cost": position.up_cost,
            "down_cost": position.down_cost,
            "complete_sets": position.complete_sets,
            "edge": position.edge,
            "hedge_ratio": position.hedge_ratio,
            "total_trades": position.total_trades,
            "avg_up_price": position.avg_up_price,
            "avg_down_price": position.avg_down_price,
            "combined_price": position.combined_price,
            "updated_at": datetime.now().isoformat()
        }

        # Read, update, write
        positions = self._read_json(self.positions_file)
        if not isinstance(positions, dict):
            positions = {}

        key = f"{position.wallet}:{position.market_slug}"
        positions[key] = pos_dict
        self._write_json(self.positions_file, positions)

    def save_market(self, market: MarketContext):
        """Save/update market metadata."""
        market_dict = {
            "slug": market.slug,
            "question": market.question,
            "condition_id": market.condition_id,
            "token_ids": market.token_ids,
            "outcomes": market.outcomes,
            "start_date": market.start_date.isoformat() if market.start_date else None,
            "end_date": market.end_date.isoformat() if market.end_date else None,
            "resolved": market.resolved,
            "winning_outcome": market.winning_outcome,
            "updated_at": datetime.now().isoformat()
        }

        # Read, update, write
        markets = self._read_json(self.markets_file)
        if not isinstance(markets, dict):
            markets = {}

        markets[market.slug] = market_dict
        self._write_json(self.markets_file, markets)

    def save_price(self, price_data: dict):
        """Save a price snapshot to prices file."""
        self._append_json(self.prices_file, price_data)

    def save_price_update(
        self,
        market_slug: str,
        outcome: str,
        price: float,
        best_bid: float,
        best_ask: float,
        timestamp: int = None
    ):
        """Save a price update from WebSocket."""
        if timestamp is None:
            timestamp = int(datetime.now().timestamp())

        price_dict = {
            "timestamp": timestamp,
            "timestamp_iso": datetime.fromtimestamp(timestamp).isoformat(),
            "market_slug": market_slug,
            "outcome": outcome,
            "price": price,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "session_id": self.session_id
        }
        self._append_json(self.prices_file, price_dict)

    def get_all_prices(self) -> List[dict]:
        """Get all price snapshots from consolidated file."""
        return self._read_json(self.prices_file)

    def get_prices_for_market(self, market_slug: str) -> List[dict]:
        """Get price snapshots for a specific market."""
        all_prices = self._read_json(self.prices_file)
        return [p for p in all_prices if p.get("market_slug") == market_slug]

    def get_all_trades(self) -> List[dict]:
        """Get all trades from consolidated file."""
        return self._read_json(self.trades_file)

    def get_all_positions(self) -> Dict[str, dict]:
        """Get all positions from consolidated file."""
        return self._read_json(self.positions_file)

    def get_all_markets(self) -> Dict[str, dict]:
        """Get all markets from consolidated file."""
        return self._read_json(self.markets_file)

    def get_session_summary(self) -> dict:
        """Get summary of current session."""
        return {
            "session_id": self.session_id,
            "db_dir": str(self.db_dir),
            "session_trades_count": len(self.session_trades),
            "total_trades_count": len(self.get_all_trades()),
            "total_markets_count": len(self.get_all_markets()),
            "total_positions_count": len(self.get_all_positions())
        }

    def flush(self):
        """Update session end time."""
        sessions = self._read_json(self.sessions_file)
        for session in sessions:
            if session["session_id"] == self.session_id:
                session["ended_at"] = datetime.now().isoformat()
                session["trades_count"] = len(self.session_trades)
                break
        self._write_json(self.sessions_file, sessions)
        print(f"Session {self.session_id} saved: {len(self.session_trades)} trades")
