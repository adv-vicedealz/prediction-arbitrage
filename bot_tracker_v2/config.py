"""
Configuration for Bot Tracker v2.
All settings in one place.
"""

import os
from pathlib import Path

# =============================================================================
# TARGET WALLETS
# =============================================================================
# Wallets to track. Key = address (lowercase), Value = display name
TARGET_WALLETS = {
    "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d": "gabagool22",
}

# =============================================================================
# API ENDPOINTS
# =============================================================================
GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# =============================================================================
# TIMING
# =============================================================================
RESOLUTION_DELAY = 120        # Wait 2 min after market ends before fetching trades
DISCOVERY_INTERVAL = 300      # Check for new user trades every 5 min
PRICE_SAVE_INTERVAL = 1.0     # Throttle price saves to 1/sec per asset
CLEANUP_INTERVAL = 3600       # Cleanup old data every hour
BACKUP_INTERVAL = 86400       # Backup database daily

# =============================================================================
# REQUEST SETTINGS
# =============================================================================
REQUEST_TIMEOUT = 30          # HTTP request timeout in seconds
MAX_RETRIES = 3               # Max retries for failed requests

# =============================================================================
# DATABASE
# =============================================================================
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DB_PATH = DATA_DIR / "tracker_v2.db"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_KEEP_DAYS = 7          # Keep backups for 7 days

# =============================================================================
# LOGGING
# =============================================================================
LOG_DIR = DATA_DIR / "logs"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB per log file
LOG_BACKUP_COUNT = 5          # Keep 5 rotated log files

# =============================================================================
# SERVER
# =============================================================================
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))

# =============================================================================
# ENSURE DIRECTORIES EXIST
# =============================================================================
def ensure_dirs():
    """Create required directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
