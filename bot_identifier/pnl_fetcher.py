"""
Fetch historical P&L data for traders.

Sources:
- All-time P&L: Goldsky PnL subgraph (pre-calculated realizedPnl per position)
- Time-period P&L: Calculated from orderbook-subgraph trades + market resolutions
"""

import requests
import time
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime, timezone

from .config import (
    GOLDSKY_ENDPOINT,
    GAMMA_API,
    REQUEST_TIMEOUT,
    RATE_LIMIT_DELAY,
    PNL_SUBGRAPH
)


@dataclass
class HistoricalPnL:
    """Historical P&L data for a trader."""
    wallet: str
    pnl_all_time: Optional[float] = None
    pnl_1d: Optional[float] = None
    pnl_1w: Optional[float] = None
    pnl_1m: Optional[float] = None


def fetch_alltime_pnl(wallet: str) -> Optional[float]:
    """
    Fetch all-time P&L from Goldsky PnL subgraph.

    Sums realizedPnl across all user positions (with pagination).

    Returns P&L in USD or None if error.
    """
    wallet = wallet.lower()
    total_pnl = 0.0
    last_id = ""
    has_positions = False

    while True:
        # Build where clause with cursor pagination
        where = f'user: "{wallet}"'
        if last_id:
            where += f', id_gt: "{last_id}"'

        query = f'''{{
            userPositions(
                first: 1000,
                where: {{ {where} }},
                orderBy: id,
                orderDirection: asc
            ) {{
                id
                realizedPnl
            }}
        }}'''

        try:
            resp = requests.post(
                PNL_SUBGRAPH,
                json={"query": query},
                timeout=REQUEST_TIMEOUT
            )
            data = resp.json()

            if "errors" in data:
                print(f"    PnL subgraph error: {data['errors']}")
                break

            positions = data.get("data", {}).get("userPositions", [])
            if not positions:
                break

            has_positions = True
            for pos in positions:
                # realizedPnl is in micro-units (divide by 1e6)
                pnl = int(pos.get("realizedPnl", 0)) / 1e6
                total_pnl += pnl

            last_id = positions[-1]["id"]

            if len(positions) < 1000:
                break

            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            print(f"    Error fetching all-time PnL for {wallet[:10]}...: {e}")
            return None

    return total_pnl if has_positions else None


def _fetch_trades_for_wallet(
    wallet: str,
    start_ts: int,
    end_ts: int,
    role: str = "maker"
) -> List[dict]:
    """
    Fetch trades for a wallet from orderbook-subgraph within time range.

    Args:
        wallet: Wallet address
        start_ts: Start timestamp
        end_ts: End timestamp
        role: "maker" or "taker"

    Returns list of raw trade events.
    """
    all_trades = []
    last_id = ""
    field = role  # "maker" or "taker"

    while True:
        where = f'{field}: "{wallet.lower()}", timestamp_gte: "{start_ts}", timestamp_lt: "{end_ts}"'
        if last_id:
            where += f', id_gt: "{last_id}"'

        query = f'''{{
            orderFilledEvents(
                first: 1000,
                where: {{ {where} }},
                orderBy: id,
                orderDirection: asc
            ) {{
                id
                timestamp
                maker
                taker
                makerAssetId
                takerAssetId
                makerAmountFilled
                takerAmountFilled
            }}
        }}'''

        try:
            resp = requests.post(
                GOLDSKY_ENDPOINT,
                json={"query": query},
                timeout=REQUEST_TIMEOUT
            )
            data = resp.json()

            if "errors" in data:
                break

            events = data.get("data", {}).get("orderFilledEvents", [])
            if not events:
                break

            all_trades.extend(events)
            last_id = events[-1]["id"]

            if len(events) < 1000:
                break

            time.sleep(RATE_LIMIT_DELAY)

        except Exception:
            break

    return all_trades


# Cache for market metadata to avoid duplicate API calls
_market_cache: Dict[str, dict] = {}


def _get_market_for_token(token_id: str) -> Optional[dict]:
    """
    Get market metadata for a token ID.

    Returns dict with {conditionId, resolved, winningOutcome, outcomes} or None.
    """
    if token_id in _market_cache:
        return _market_cache[token_id]

    try:
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"clob_token_ids": token_id},
            timeout=REQUEST_TIMEOUT
        )

        if resp.status_code != 200:
            return None

        markets = resp.json()
        if not markets:
            return None

        market = markets[0] if isinstance(markets, list) else markets

        # Determine winning outcome
        import json
        outcome_prices = market.get("outcomePrices")
        outcomes = market.get("outcomes", "[]")

        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if isinstance(outcome_prices, str):
            outcome_prices = json.loads(outcome_prices)

        winning_outcome = None
        if outcome_prices and market.get("closed"):
            for i, price in enumerate(outcome_prices):
                if float(price) == 1.0 and i < len(outcomes):
                    winning_outcome = outcomes[i].lower()
                    break

        result = {
            "conditionId": market.get("conditionId"),
            "resolved": market.get("closed", False),
            "winningOutcome": winning_outcome,
            "outcomes": outcomes,
            "tokenId": token_id
        }

        _market_cache[token_id] = result
        return result

    except Exception:
        return None


def _calculate_pnl_from_trades(trades: List[dict], wallet: str) -> float:
    """
    Calculate P&L from a list of trades for resolved markets.

    Groups trades by token, gets market resolution, calculates P&L.
    """
    wallet = wallet.lower()
    pnl = 0.0

    # Group trades by token
    trades_by_token: Dict[str, List[dict]] = {}
    for trade in trades:
        # Determine which token is being traded
        if trade["makerAssetId"] != "0":
            token_id = trade["makerAssetId"]
        else:
            token_id = trade["takerAssetId"]

        if token_id == "0":
            continue  # Skip USDC-only trades

        if token_id not in trades_by_token:
            trades_by_token[token_id] = []
        trades_by_token[token_id].append(trade)

    # Calculate P&L per token/market
    for token_id, token_trades in trades_by_token.items():
        market = _get_market_for_token(token_id)
        if not market or not market.get("resolved"):
            continue  # Skip unresolved markets

        winning_outcome = market.get("winningOutcome")
        if not winning_outcome:
            continue

        # Calculate net position and cost
        net_shares = 0.0
        net_cost = 0.0

        for trade in token_trades:
            is_maker = trade["maker"].lower() == wallet
            is_taker = trade["taker"].lower() == wallet

            if trade["makerAssetId"] == "0":
                # Maker bought shares (paid USDC)
                usdc = int(trade["makerAmountFilled"]) / 1e6
                shares = int(trade["takerAmountFilled"]) / 1e6
                if is_maker:
                    net_shares += shares
                    net_cost += usdc
                elif is_taker:
                    net_shares -= shares
                    net_cost -= usdc
            else:
                # Maker sold shares (received USDC)
                shares = int(trade["makerAmountFilled"]) / 1e6
                usdc = int(trade["takerAmountFilled"]) / 1e6
                if is_maker:
                    net_shares -= shares
                    net_cost -= usdc
                elif is_taker:
                    net_shares += shares
                    net_cost += usdc

        # Determine if this token won
        # Need to check if token matches winning outcome
        outcomes = market.get("outcomes", [])
        token_won = False

        # Token ID position in clob_token_ids corresponds to outcomes array index
        # We already know which outcome won, need to check if this token is the winner
        try:
            resp = requests.get(
                f"{GAMMA_API}/markets",
                params={"clob_token_ids": token_id},
                timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 200:
                markets_data = resp.json()
                if markets_data:
                    m = markets_data[0] if isinstance(markets_data, list) else markets_data
                    import json
                    clob_tokens = m.get("clobTokenIds", "[]")
                    if isinstance(clob_tokens, str):
                        clob_tokens = json.loads(clob_tokens)

                    # Find which outcome this token represents
                    for i, t_id in enumerate(clob_tokens):
                        if t_id == token_id and i < len(outcomes):
                            token_outcome = outcomes[i].lower()
                            token_won = (token_outcome == winning_outcome)
                            break
        except Exception:
            pass

        # Calculate P&L
        if token_won:
            pnl += (net_shares * 1.0) - net_cost
        else:
            pnl += (net_shares * 0.0) - net_cost

        time.sleep(RATE_LIMIT_DELAY * 0.5)

    return pnl


def fetch_timeperiod_pnl(wallet: str, days: int) -> Optional[float]:
    """
    Calculate P&L for a specific time period.

    Args:
        wallet: Wallet address
        days: Number of days (1, 7, or 30)

    Returns P&L in USD or None if no resolved trades in period.
    """
    now = int(datetime.now(timezone.utc).timestamp())
    start_ts = now - (days * 24 * 3600)

    # Fetch trades as both maker and taker
    maker_trades = _fetch_trades_for_wallet(wallet, start_ts, now, "maker")
    time.sleep(RATE_LIMIT_DELAY)
    taker_trades = _fetch_trades_for_wallet(wallet, start_ts, now, "taker")

    all_trades = maker_trades + taker_trades

    if not all_trades:
        return None

    # Deduplicate by trade ID
    seen_ids = set()
    unique_trades = []
    for t in all_trades:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            unique_trades.append(t)

    return _calculate_pnl_from_trades(unique_trades, wallet)


def fetch_historical_pnl(wallet: str, include_periods: bool = True) -> HistoricalPnL:
    """
    Fetch all historical P&L data for a wallet.

    Args:
        wallet: Wallet address
        include_periods: If True, also fetch 1d/1w/1m P&L (slower)

    Returns HistoricalPnL dataclass.
    """
    result = HistoricalPnL(wallet=wallet)

    # All-time P&L from subgraph
    result.pnl_all_time = fetch_alltime_pnl(wallet)
    time.sleep(RATE_LIMIT_DELAY)

    if include_periods:
        # Time-period P&L (calculated from trades)
        result.pnl_1d = fetch_timeperiod_pnl(wallet, 1)
        time.sleep(RATE_LIMIT_DELAY)

        result.pnl_1w = fetch_timeperiod_pnl(wallet, 7)
        time.sleep(RATE_LIMIT_DELAY)

        result.pnl_1m = fetch_timeperiod_pnl(wallet, 30)

    return result


def fetch_historical_pnl_batch(
    wallets: List[str],
    include_periods: bool = False,
    limit: int = 50
) -> Dict[str, HistoricalPnL]:
    """
    Fetch historical P&L for multiple wallets.

    Args:
        wallets: List of wallet addresses
        include_periods: If True, fetch 1d/1w/1m (much slower)
        limit: Max wallets to process

    Returns dict mapping wallet -> HistoricalPnL.
    """
    results = {}

    for i, wallet in enumerate(wallets[:limit]):
        if (i + 1) % 10 == 0:
            print(f"  Fetching P&L: {i + 1}/{min(len(wallets), limit)}")

        results[wallet.lower()] = fetch_historical_pnl(wallet, include_periods)
        time.sleep(RATE_LIMIT_DELAY)

    return results
