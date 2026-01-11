"""
Pydantic models for API responses.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class Trade(BaseModel):
    """Trade event from Polymarket."""
    id: str
    tx_hash: str = ""
    timestamp: int
    wallet: str
    wallet_name: str = ""
    role: str = "taker"
    side: str  # BUY or SELL
    outcome: str  # Up or Down
    shares: float
    usdc: float
    price: float
    fee: float = 0
    market_slug: str
    market_question: str = ""


class Position(BaseModel):
    """Computed position for a wallet in a market."""
    wallet: str
    wallet_name: str
    market_slug: str
    up_shares: float
    down_shares: float
    up_cost: float
    down_cost: float
    up_revenue: float
    down_revenue: float
    complete_sets: float
    unhedged_up: float
    unhedged_down: float
    avg_up_price: float
    avg_down_price: float
    combined_price: float
    edge: float
    hedge_ratio: float
    total_trades: int
    buy_trades: int
    sell_trades: int
    maker_trades: int = 0
    taker_trades: int = 0
    first_trade_ts: int
    last_trade_ts: int


class Market(BaseModel):
    """Market from Polymarket."""
    slug: str
    condition_id: str
    question: str = ""
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    up_token_id: Optional[str] = None
    down_token_id: Optional[str] = None
    resolved: bool = False
    winning_outcome: Optional[str] = None
    trades_fetched: bool = False


class Price(BaseModel):
    """Price snapshot."""
    timestamp: int
    timestamp_iso: str = ""
    market_slug: str
    outcome: str
    price: float
    best_bid: float = 0
    best_ask: float = 0


class Wallet(BaseModel):
    """Tracked wallet."""
    address: str
    name: str


class Trader(BaseModel):
    """Top trader entry."""
    wallet: str
    name: str
    link: str = ""
    all_time_profit: float = 0


class TrackerConfig(BaseModel):
    """Tracker configuration response."""
    wallet: Wallet
    market_filter: str = ""
    buy_only: bool = False
    running: bool = True


class TrackerStats(BaseModel):
    """Stats for WebSocket broadcast."""
    total_wallets: int
    total_markets: int
    total_positions: int
    total_trades: int
    connected_clients: int = 0


class MarketInfo(BaseModel):
    """Market info for tracking-info response."""
    slug: str
    question: str
    trades_captured: int
    first_trade_time: Optional[str] = None
    last_trade_time: Optional[str] = None
    tracking_duration_mins: float = 0
    market_end_time: Optional[str] = None
    resolved: bool = False
    winning_outcome: Optional[str] = None


class TrackingInfo(BaseModel):
    """Tracking info response."""
    tracking_started: str
    uptime_seconds: float
    total_trades_captured: int
    markets: List[MarketInfo]


class PriceStreamStatus(BaseModel):
    """Price stream status."""
    connected: bool
    running: bool
    subscribed_assets: int
    assets: List[str]


class WSMessage(BaseModel):
    """WebSocket message format."""
    type: str
    data: dict
    timestamp: str
    sequence: int = 0
