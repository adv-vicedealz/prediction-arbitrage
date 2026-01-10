"""Pydantic models for the bot tracker."""

from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class TradeEvent(BaseModel):
    """Real-time trade event from Goldsky."""
    id: str
    tx_hash: str
    timestamp: int
    wallet: str
    wallet_name: str
    role: str  # "maker" or "taker"
    side: str  # "BUY" or "SELL"
    outcome: str  # "Up" or "Down"
    shares: float
    usdc: float
    price: float
    fee: float
    market_slug: str
    market_question: str = ""

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MarketContext(BaseModel):
    """Current market state with orderbook data."""
    slug: str
    question: str
    condition_id: str
    token_ids: Dict[str, str]  # {"up": "...", "down": "..."}
    outcomes: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    time_to_resolution_mins: float = 0
    resolved: bool = False
    winning_outcome: Optional[str] = None
    # Orderbook data
    up_best_bid: Optional[float] = None
    up_best_ask: Optional[float] = None
    down_best_bid: Optional[float] = None
    down_best_ask: Optional[float] = None
    combined_bid: Optional[float] = None  # up_best_bid + down_best_bid
    spread: Optional[float] = None  # 1 - combined_bid (potential edge)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class WalletPosition(BaseModel):
    """Current position for a wallet in a specific market."""
    wallet: str
    wallet_name: str
    market_slug: str
    # Position data
    up_shares: float = 0
    down_shares: float = 0
    up_cost: float = 0
    down_cost: float = 0
    up_revenue: float = 0  # From selling UP
    down_revenue: float = 0  # From selling DOWN
    # Derived metrics
    complete_sets: float = 0  # min(up_shares, down_shares)
    unhedged_up: float = 0  # up_shares - complete_sets
    unhedged_down: float = 0  # down_shares - complete_sets
    avg_up_price: float = 0
    avg_down_price: float = 0
    combined_price: float = 0  # avg_up_price + avg_down_price
    edge: float = 0  # 1 - combined_price (if < 0, locked in profit)
    hedge_ratio: float = 0  # min(up, down) / max(up, down)
    # Trade counts
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    maker_trades: int = 0
    taker_trades: int = 0
    # Timing
    first_trade_ts: int = 0
    last_trade_ts: int = 0


class TimingPattern(BaseModel):
    """Timing analysis for a wallet in a market."""
    wallet: str
    wallet_name: str
    market_slug: str
    # Timing metrics
    time_to_start_mins: float = 0  # First trade relative to market start
    time_to_end_mins: float = 0  # Last trade relative to market end
    trading_window_mins: float = 0  # Duration of trading activity
    trades_per_minute: float = 0
    # Indicators
    early_trader: bool = False  # Started within 2 mins of market open
    late_closer: bool = False  # Active within 2 mins of market close


class PricePattern(BaseModel):
    """Price strategy analysis for a wallet."""
    wallet: str
    wallet_name: str
    market_slug: str
    # Price metrics
    avg_buy_price_up: float = 0
    avg_buy_price_down: float = 0
    avg_sell_price_up: float = 0
    avg_sell_price_down: float = 0
    combined_buy_price: float = 0  # avg_buy_up + avg_buy_down
    spread_captured: float = 0  # Avg sell - avg buy (profit per share)
    # Indicators
    bought_below_dollar: bool = False  # combined_buy_price < 1.0
    maker_percentage: float = 0


class HedgePattern(BaseModel):
    """Hedging behavior analysis for a wallet."""
    wallet: str
    wallet_name: str
    market_slug: str
    # Hedge metrics
    hedge_ratio: float = 0  # min(up, down) / max(up, down)
    up_shares: float = 0
    down_shares: float = 0
    # Indicators
    is_fully_hedged: bool = False  # ratio > 0.95
    is_directional: bool = False  # ratio < 0.3
    dominant_side: str = "BALANCED"  # "UP", "DOWN", or "BALANCED"
    strategy_type: str = "UNKNOWN"  # "ARBITRAGE", "MARKET_MAKING", "DIRECTIONAL"


class TrackerState(BaseModel):
    """Overall state of the tracker for API responses."""
    connected_clients: int = 0
    tracked_wallets: int = 0
    active_markets: int = 0
    total_trades_seen: int = 0
    last_trade_ts: Optional[int] = None
    uptime_seconds: float = 0
