"""
Data fetching for Polymarket trades - uses Data API primarily
Falls back to Polygon RPC if needed
"""

import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

from .config import (
    POLYGON_RPC,
    DATA_API,
    CTF_EXCHANGE,
    NEG_RISK_EXCHANGE,
    API_RATE_LIMIT_DELAY
)


class BlockchainClient:
    """Client for fetching Polymarket trades"""

    def __init__(self, rpc_url: str = POLYGON_RPC):
        self.rpc_url = rpc_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolymarketAnalyzer/1.0',
            'Accept': 'application/json'
        })
        self.last_call = 0

    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_call
        if elapsed < API_RATE_LIMIT_DELAY:
            time.sleep(API_RATE_LIMIT_DELAY - elapsed)
        self.last_call = time.time()

    def fetch_wallet_trades_from_api(
        self,
        wallet_address: str,
        days: int = 7,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Fetch trades from Polymarket Data API using time-based pagination.

        Uses sliding time windows to bypass the 10,000 offset limit.
        For high-frequency traders, this allows fetching unlimited history.
        """
        wallet_address = wallet_address.lower()
        all_trades = []
        seen_tx_hashes = set()  # Deduplicate across time windows

        # Start from now and work backwards
        current_end = datetime.now()
        target_start = current_end - timedelta(days=days)

        # Time window size - start with 1 hour, adjust if needed
        window_hours = 1

        print(f"Fetching from Data API (last {days} days)...")
        print(f"Using time-based pagination with {window_hours}h windows")

        windows_processed = 0
        while current_end > target_start:
            window_start = current_end - timedelta(hours=window_hours)
            if window_start < target_start:
                window_start = target_start

            start_ts = int(window_start.timestamp())
            end_ts = int(current_end.timestamp())

            window_trades = self._fetch_time_window(
                wallet_address, start_ts, end_ts, limit, seen_tx_hashes
            )

            if window_trades:
                all_trades.extend(window_trades)
                windows_processed += 1

                print(f"  Window {windows_processed}: {window_start.strftime('%m/%d %H:%M')} - {current_end.strftime('%H:%M')} "
                      f"| {len(window_trades)} new trades | Total: {len(all_trades)}")

            # Move to next window
            current_end = window_start

            # Rate limit between windows
            time.sleep(0.1)

        print(f"Completed {windows_processed} time windows")
        return all_trades

    def _fetch_time_window(
        self,
        wallet_address: str,
        start_ts: int,
        end_ts: int,
        limit: int,
        seen_tx_hashes: set
    ) -> List[Dict[str, Any]]:
        """Fetch all trades within a specific time window"""
        window_trades = []
        offset = 0
        max_offset = 10000

        while offset < max_offset:
            self._rate_limit()

            try:
                resp = self.session.get(
                    f"{DATA_API}/activity",
                    params={
                        'user': wallet_address,
                        'type': 'TRADE',
                        'limit': limit,
                        'offset': offset,
                        'start': start_ts,
                        'end': end_ts,
                        'sortBy': 'TIMESTAMP',
                        'sortDirection': 'DESC'
                    },
                    timeout=30
                )
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                # Parse and deduplicate
                for item in data:
                    tx_hash = item.get('transactionHash', '')
                    if tx_hash and tx_hash not in seen_tx_hashes:
                        seen_tx_hashes.add(tx_hash)
                        trade = self._parse_api_trade(item, wallet_address)
                        if trade:
                            window_trades.append(trade)

                if len(data) < limit:
                    break

                offset += limit

            except requests.exceptions.RequestException as e:
                print(f"API error: {e}")
                if "429" in str(e):
                    print("Rate limited, waiting 5s...")
                    time.sleep(5)
                    continue
                break

        return window_trades

    def _parse_api_trade(
        self,
        item: Dict[str, Any],
        wallet_address: str
    ) -> Optional[Dict[str, Any]]:
        """Parse a trade from the Data API response"""
        try:
            timestamp = datetime.fromtimestamp(item.get('timestamp', 0))
            side = item.get('side', '').upper()
            outcome = item.get('outcome', '')

            # Determine contract type from title or other fields
            title = item.get('title', '')
            # NegRisk markets are typically multi-outcome (not just Yes/No)
            contract = 'NegRisk' if 'Up or Down' in title else 'CTF'

            return {
                'transaction_hash': item.get('transactionHash', ''),
                'block_number': None,  # Not available from API
                'timestamp': timestamp,
                'wallet_address': wallet_address,
                'role': 'unknown',  # API doesn't distinguish maker/taker
                'token_id': item.get('asset', ''),
                'condition_id': item.get('conditionId', ''),
                'outcome': outcome,
                'side': side,
                'shares': float(item.get('size', 0)),
                'usdc_amount': float(item.get('usdcSize', 0)),
                'price': float(item.get('price', 0)),
                'contract': contract,
                'market_question': item.get('title', ''),
                'market_slug': item.get('slug', ''),
                'market_category': None,  # Will be enriched later if needed
            }
        except Exception as e:
            print(f"Error parsing trade: {e}")
            return None

    def fetch_wallet_trades(
        self,
        wallet_address: str,
        days: int = 7,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Main method: Fetch all trades for a wallet in the last N days

        Uses Data API (more reliable than direct blockchain queries)
        """
        trades = self.fetch_wallet_trades_from_api(wallet_address, days)
        print(f"Total trades fetched: {len(trades)}")
        return trades


# Keep legacy methods for potential future use with archive nodes
class LegacyBlockchainClient:
    """Legacy client using direct RPC calls - requires archive node"""

    def __init__(self, rpc_url: str = POLYGON_RPC):
        try:
            from web3 import Web3
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            self.connected = self.w3.is_connected()
        except Exception:
            self.connected = False

    def get_current_block(self) -> int:
        """Get current block number"""
        if not self.connected:
            return 0
        return self.w3.eth.block_number

    def get_block_timestamp(self, block_number: int) -> datetime:
        """Get timestamp for a specific block"""
        if not self.connected:
            return datetime.now()
        block = self.w3.eth.get_block(block_number)
        return datetime.fromtimestamp(block.timestamp)
