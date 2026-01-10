"""
Polymarket API client for market metadata enrichment
"""

import time
import json
import requests
from typing import Dict, Any, Optional, List

from .config import GAMMA_API, DATA_API, API_RATE_LIMIT_DELAY


class PolymarketAPI:
    """Client for Polymarket Gamma and Data APIs"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolymarketAnalyzer/1.0',
            'Accept': 'application/json'
        })
        self.last_call = 0
        self._cache: Dict[str, Dict] = {}

    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_call
        if elapsed < API_RATE_LIMIT_DELAY:
            time.sleep(API_RATE_LIMIT_DELAY - elapsed)
        self.last_call = time.time()

    def get_market_by_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Get market metadata from Gamma API using clob_token_ids

        Returns market dict or None if not found
        """
        # Check cache first
        if token_id in self._cache:
            return self._cache[token_id]

        self._rate_limit()

        try:
            resp = self.session.get(
                f"{GAMMA_API}/markets",
                params={"clob_token_ids": token_id},
                timeout=15
            )
            resp.raise_for_status()
            markets = resp.json()

            if markets and len(markets) > 0:
                market = markets[0]
                # Cache by token_id
                self._cache[token_id] = market
                # Also cache by all token IDs in this market
                clob_ids = market.get('clobTokenIds', '[]')
                if isinstance(clob_ids, str):
                    try:
                        clob_ids = json.loads(clob_ids)
                    except:
                        clob_ids = []
                for cid in clob_ids:
                    self._cache[cid] = market
                return market

        except requests.exceptions.RequestException as e:
            print(f"API error for token {token_id[:20]}...: {e}")
        except Exception as e:
            print(f"Error parsing response for token {token_id[:20]}...: {e}")

        return None

    def get_market_by_condition(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Get market by condition ID"""
        cache_key = f"condition:{condition_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        self._rate_limit()

        try:
            resp = self.session.get(
                f"{GAMMA_API}/markets",
                params={"condition_id": condition_id},
                timeout=15
            )
            resp.raise_for_status()
            markets = resp.json()

            if markets and len(markets) > 0:
                market = markets[0]
                self._cache[cache_key] = market
                return market

        except Exception as e:
            print(f"Error fetching market by condition: {e}")

        return None

    def get_outcome_from_token(self, token_id: str, market: Dict[str, Any]) -> str:
        """
        Determine if token represents Yes/No or Up/Down outcome

        Returns outcome string or 'Unknown'
        """
        clob_ids = market.get('clobTokenIds', '[]')
        outcomes = market.get('outcomes', '["Yes", "No"]')

        # Parse if strings
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except:
                clob_ids = []

        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except:
                outcomes = ['Yes', 'No']

        # Match token to outcome
        if len(clob_ids) >= 2 and len(outcomes) >= 2:
            if token_id == clob_ids[0]:
                return outcomes[0]
            elif token_id == clob_ids[1]:
                return outcomes[1]

        return 'Unknown'

    def enrich_trades_batch(
        self,
        trades: List[Dict[str, Any]],
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Enrich a batch of trades with market metadata

        Modifies trades in place and returns them
        """
        # Get unique token IDs
        token_ids = set(t['token_id'] for t in trades)
        total = len(token_ids)
        print(f"Enriching {total} unique tokens...")

        # Fetch markets for each token
        for i, token_id in enumerate(token_ids):
            market = self.get_market_by_token(token_id)

            if progress_callback:
                progress_callback(i + 1, total)

        # Now enrich trades from cache
        for trade in trades:
            market = self._cache.get(trade['token_id'])
            if market:
                trade['condition_id'] = market.get('conditionId')
                trade['market_question'] = market.get('question')
                trade['market_slug'] = market.get('slug')
                trade['market_category'] = market.get('category')
                trade['outcome'] = self.get_outcome_from_token(
                    trade['token_id'], market
                )
                trade['market_resolved'] = market.get('closed', False)
                trade['outcome_prices'] = market.get('outcomePrices')

        return trades

    def get_market_for_db(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """Format market data for database insertion"""
        return {
            'condition_id': market.get('conditionId'),
            'question': market.get('question'),
            'slug': market.get('slug'),
            'category': market.get('category'),
            'end_date': market.get('endDate'),
            'outcomes': json.dumps(market.get('outcomes', [])) if isinstance(
                market.get('outcomes'), list
            ) else market.get('outcomes'),
            'clob_token_ids': json.dumps(market.get('clobTokenIds', [])) if isinstance(
                market.get('clobTokenIds'), list
            ) else market.get('clobTokenIds'),
            'resolution_source': market.get('resolutionSource'),
            'resolved': 1 if market.get('closed') else 0,
            'outcome_prices': market.get('outcomePrices')
        }

    def get_cached_markets(self) -> List[Dict[str, Any]]:
        """Get all cached markets for database storage"""
        seen_conditions = set()
        markets = []

        for data in self._cache.values():
            condition_id = data.get('conditionId')
            if condition_id and condition_id not in seen_conditions:
                seen_conditions.add(condition_id)
                markets.append(self.get_market_for_db(data))

        return markets

    def clear_cache(self):
        """Clear the market cache"""
        self._cache.clear()
