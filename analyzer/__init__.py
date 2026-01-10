"""
Polymarket Trade Data Analyzer
Downloads and analyzes trading history for specified wallets
"""

from .config import *
from .database import Database
from .blockchain import BlockchainClient
from .api import PolymarketAPI
from .fetcher import TradeFetcher
