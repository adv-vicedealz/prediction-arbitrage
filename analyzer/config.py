"""
Configuration constants for Polymarket analyzer
"""

# Polygon RPC endpoint (free, public)
POLYGON_RPC = "https://polygon-rpc.com"

# Polymarket exchange contracts on Polygon
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEG_RISK_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"

# Polymarket API endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# Polygon block time (~2 seconds)
BLOCKS_PER_SECOND = 0.5
BLOCKS_PER_DAY = int(24 * 60 * 60 * BLOCKS_PER_SECOND)  # ~43,200

# Batch sizes for fetching
BLOCK_BATCH_SIZE = 2000  # Blocks per RPC request
API_RATE_LIMIT_DELAY = 0.2  # Seconds between API calls

# USDC asset ID threshold (USDC has small ID, outcome tokens have large IDs)
USDC_ASSET_THRESHOLD = 1000

# OrderFilled event ABI (same for both CTF and NegRisk exchanges)
ORDER_FILLED_ABI = [{
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "maker", "type": "address"},
        {"indexed": False, "name": "taker", "type": "address"},
        {"indexed": False, "name": "makerAssetId", "type": "uint256"},
        {"indexed": False, "name": "takerAssetId", "type": "uint256"},
        {"indexed": False, "name": "makerAmountFilled", "type": "uint256"},
        {"indexed": False, "name": "takerAmountFilled", "type": "uint256"}
    ],
    "name": "OrderFilled",
    "type": "event"
}]

# Default database path
DEFAULT_DB_PATH = "data/trades.db"
