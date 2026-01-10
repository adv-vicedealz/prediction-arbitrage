"""
Aggregate trades by wallet address and compute per-trader metrics.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .market_fetcher import ParsedTrade


@dataclass
class TraderMetrics:
    """Aggregated metrics for a single trader."""
    wallet: str

    # Trade counts
    total_trades: int = 0
    maker_trades: int = 0
    taker_trades: int = 0

    # Volume
    total_volume_usdc: float = 0.0
    buy_volume_usdc: float = 0.0
    sell_volume_usdc: float = 0.0

    # Positions by outcome
    up_bought: float = 0.0
    up_sold: float = 0.0
    down_bought: float = 0.0
    down_sold: float = 0.0

    # Costs and revenue
    up_cost: float = 0.0      # USDC spent buying Up
    down_cost: float = 0.0    # USDC spent buying Down
    up_revenue: float = 0.0   # USDC received selling Up
    down_revenue: float = 0.0  # USDC received selling Down

    # Fees
    total_fees: float = 0.0

    # Timing
    first_trade_ts: int = 0
    last_trade_ts: int = 0

    # P&L (computed after aggregation)
    realized_pnl: Optional[float] = None

    # Markets traded
    markets_traded: int = 0

    @property
    def up_net(self) -> float:
        """Net Up position (bought - sold)."""
        return self.up_bought - self.up_sold

    @property
    def down_net(self) -> float:
        """Net Down position (bought - sold)."""
        return self.down_bought - self.down_sold

    @property
    def maker_ratio(self) -> float:
        """Fraction of trades where trader was maker."""
        if self.total_trades == 0:
            return 0.0
        return self.maker_trades / self.total_trades

    @property
    def trading_duration_mins(self) -> float:
        """Duration from first to last trade in minutes."""
        if self.last_trade_ts <= self.first_trade_ts:
            return 0.0
        return (self.last_trade_ts - self.first_trade_ts) / 60.0

    @property
    def trades_per_minute(self) -> float:
        """Average trades per minute."""
        if self.trading_duration_mins <= 0:
            return 0.0
        return self.total_trades / self.trading_duration_mins

    @property
    def avg_up_buy_price(self) -> float:
        """Average price paid for Up shares."""
        if self.up_bought <= 0:
            return 0.0
        return self.up_cost / self.up_bought

    @property
    def avg_down_buy_price(self) -> float:
        """Average price paid for Down shares."""
        if self.down_bought <= 0:
            return 0.0
        return self.down_cost / self.down_bought

    @property
    def combined_buy_price(self) -> float:
        """Combined price of buying both outcomes (for arbitrage detection)."""
        up_price = self.avg_up_buy_price
        down_price = self.avg_down_buy_price
        if up_price > 0 and down_price > 0:
            return up_price + down_price
        return 0.0

    @property
    def edge(self) -> float:
        """Arbitrage edge: 1 - combined_buy_price."""
        combined = self.combined_buy_price
        if combined > 0:
            return 1.0 - combined
        return 0.0

    @property
    def position_balance_ratio(self) -> float:
        """
        Ratio of smaller to larger net position.
        1.0 = perfectly balanced (arbitrage), 0.0 = one-sided bet.
        """
        up = abs(self.up_net)
        down = abs(self.down_net)
        if up == 0 and down == 0:
            return 0.0
        if up == 0 or down == 0:
            return 0.0
        return min(up, down) / max(up, down)


def aggregate_trades(trades: List[ParsedTrade]) -> Dict[str, TraderMetrics]:
    """
    Group trades by wallet address and compute metrics.

    Args:
        trades: List of ParsedTrade objects from all markets

    Returns:
        Dict mapping wallet address to TraderMetrics
    """
    traders: Dict[str, TraderMetrics] = {}

    for trade in trades:
        wallet = trade.wallet

        if wallet not in traders:
            traders[wallet] = TraderMetrics(
                wallet=wallet,
                first_trade_ts=trade.timestamp,
                last_trade_ts=trade.timestamp
            )

        t = traders[wallet]
        t.total_trades += 1

        # Role
        if trade.role == "maker":
            t.maker_trades += 1
        else:
            t.taker_trades += 1

        # Volume and positions
        if trade.side == "BUY":
            t.buy_volume_usdc += trade.usdc
            t.total_volume_usdc += trade.usdc

            if trade.outcome.lower() == "up":
                t.up_bought += trade.shares
                t.up_cost += trade.usdc
            else:
                t.down_bought += trade.shares
                t.down_cost += trade.usdc
        else:  # SELL
            t.sell_volume_usdc += trade.usdc
            t.total_volume_usdc += trade.usdc

            if trade.outcome.lower() == "up":
                t.up_sold += trade.shares
                t.up_revenue += trade.usdc
            else:
                t.down_sold += trade.shares
                t.down_revenue += trade.usdc

        # Fees
        t.total_fees += trade.fee

        # Timestamps
        if trade.timestamp < t.first_trade_ts:
            t.first_trade_ts = trade.timestamp
        if trade.timestamp > t.last_trade_ts:
            t.last_trade_ts = trade.timestamp

    return traders


def calculate_pnl(metrics: TraderMetrics, winning_outcome: Optional[str]) -> float:
    """
    Calculate P&L based on market resolution.

    If "Up" wins: Up positions pay $1, Down positions pay $0
    If "Down" wins: Down positions pay $1, Up positions pay $0

    P&L = payout - total_cost + total_revenue - fees
    """
    if not winning_outcome:
        return 0.0

    winning_outcome = winning_outcome.lower()

    if winning_outcome == "up":
        # Up holders get $1 per share, Down holders get $0
        payout = metrics.up_net * 1.0 + metrics.down_net * 0.0
    elif winning_outcome == "down":
        # Down holders get $1 per share, Up holders get $0
        payout = metrics.up_net * 0.0 + metrics.down_net * 1.0
    else:
        return 0.0

    total_cost = metrics.up_cost + metrics.down_cost
    total_revenue = metrics.up_revenue + metrics.down_revenue

    return payout - total_cost + total_revenue - metrics.total_fees


def aggregate_across_markets(
    all_market_traders: List[Dict[str, TraderMetrics]]
) -> Dict[str, TraderMetrics]:
    """
    Aggregate trader metrics across multiple markets.

    Args:
        all_market_traders: List of per-market trader dicts

    Returns:
        Combined metrics across all markets
    """
    combined: Dict[str, TraderMetrics] = {}

    for market_traders in all_market_traders:
        for wallet, metrics in market_traders.items():
            if wallet not in combined:
                combined[wallet] = TraderMetrics(
                    wallet=wallet,
                    first_trade_ts=metrics.first_trade_ts,
                    last_trade_ts=metrics.last_trade_ts
                )

            c = combined[wallet]

            # Add counts
            c.total_trades += metrics.total_trades
            c.maker_trades += metrics.maker_trades
            c.taker_trades += metrics.taker_trades
            c.markets_traded += 1

            # Add volumes
            c.total_volume_usdc += metrics.total_volume_usdc
            c.buy_volume_usdc += metrics.buy_volume_usdc
            c.sell_volume_usdc += metrics.sell_volume_usdc

            # Add positions
            c.up_bought += metrics.up_bought
            c.up_sold += metrics.up_sold
            c.down_bought += metrics.down_bought
            c.down_sold += metrics.down_sold

            # Add costs/revenue
            c.up_cost += metrics.up_cost
            c.down_cost += metrics.down_cost
            c.up_revenue += metrics.up_revenue
            c.down_revenue += metrics.down_revenue

            # Add fees and P&L
            c.total_fees += metrics.total_fees
            if metrics.realized_pnl is not None:
                if c.realized_pnl is None:
                    c.realized_pnl = 0.0
                c.realized_pnl += metrics.realized_pnl

            # Update timestamps
            if metrics.first_trade_ts < c.first_trade_ts:
                c.first_trade_ts = metrics.first_trade_ts
            if metrics.last_trade_ts > c.last_trade_ts:
                c.last_trade_ts = metrics.last_trade_ts

    return combined
