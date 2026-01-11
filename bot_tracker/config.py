"""Configuration constants for bot tracker."""

import os

# API Endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
GOLDSKY_ENDPOINT = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"
CLOB_API = "https://clob.polymarket.com"

# Polymarket Data API (for trades and positions)
POLYMARKET_DATA_API = "https://data-api.polymarket.com"

# Polymarket WebSocket (for real-time market prices)
POLYMARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# Target wallets to track
TARGET_WALLETS = {
    "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d": "gabagool22",
}

# Polling configuration
TRADE_POLL_INTERVAL = 2  # seconds (faster for near real-time)
MARKET_POLL_INTERVAL = 30  # seconds for market discovery
REQUEST_TIMEOUT = 30  # seconds

# Server configuration
WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8765"))
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("PORT", os.getenv("HTTP_PORT", "8000")))  # Railway uses PORT

# Markets to track (BTC and ETH Up/Down 15-minute markets)
MARKET_SLUGS_PATTERN = r"(btc|eth)-updown-15m-\d+"
MARKET_FILTER_ENABLED = True  # Only track BTC/ETH 15m markets

# Track only BUY trades (True) or all trades (False)
BUY_ONLY = True  # Only track BUY trades
