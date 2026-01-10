"""Configuration constants for bot identifier."""

# API Endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
GOLDSKY_ENDPOINT = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"
PNL_SUBGRAPH = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/pnl-subgraph/0.0.14/gn"

# Default markets to analyze
DEFAULT_MARKET_URLS = [
    "https://polymarket.com/event/eth-updown-15m-1768037400/eth-updown-15m-1768037400",
    "https://polymarket.com/event/eth-updown-15m-1768036500/eth-updown-15m-1768036500",
    "https://polymarket.com/event/btc-updown-15m-1768037400/btc-updown-15m-1768037400",
    "https://polymarket.com/event/btc-updown-15m-1768036500/btc-updown-15m-1768036500",
    "https://polymarket.com/event/eth-updown-15m-1768035600/eth-updown-15m-1768035600",
    "https://polymarket.com/event/btc-updown-15m-1768034700/btc-updown-15m-1768034700",
]

# Bot score thresholds
BOT_SCORE_THRESHOLDS = {
    "high_maker_ratio": 0.70,      # > 70% maker trades
    "high_trade_count": 100,        # > 100 trades in markets
    "balanced_positions": 0.80,     # up/down ratio > 0.8
    "fast_trading": 5.0,            # > 5 trades per minute
}

# Request settings
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 0.2  # seconds between requests
