"""
Position tracker - maintains running positions per wallet per market.
"""

from typing import Dict, List
from collections import defaultdict

from .models import TradeEvent, WalletPosition


class PositionTracker:
    """Tracks running positions for each wallet in each market."""

    def __init__(self):
        # positions[wallet][market_slug] = WalletPosition
        self.positions: Dict[str, Dict[str, WalletPosition]] = defaultdict(dict)
        # Track total shares bought (not net) for avg price calculation
        self._up_shares_bought: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._down_shares_bought: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def update_position(self, trade: TradeEvent) -> WalletPosition:
        """Update position based on a new trade."""
        wallet = trade.wallet.lower()
        market = trade.market_slug

        # Create position if it doesn't exist
        if market not in self.positions[wallet]:
            self.positions[wallet][market] = WalletPosition(
                wallet=wallet,
                wallet_name=trade.wallet_name,
                market_slug=market,
                first_trade_ts=trade.timestamp
            )

        pos = self.positions[wallet][market]

        # Update trade counts
        pos.total_trades += 1
        if trade.side == "BUY":
            pos.buy_trades += 1
        else:
            pos.sell_trades += 1

        if trade.role == "maker":
            pos.maker_trades += 1
        else:
            pos.taker_trades += 1

        # Update first/last trade timestamps
        if pos.first_trade_ts == 0 or trade.timestamp < pos.first_trade_ts:
            pos.first_trade_ts = trade.timestamp
        if trade.timestamp > pos.last_trade_ts:
            pos.last_trade_ts = trade.timestamp

        # Update position based on trade
        outcome = trade.outcome.lower()

        if trade.side == "BUY":
            if outcome == "up":
                pos.up_shares += trade.shares
                pos.up_cost += trade.usdc
                self._up_shares_bought[wallet][market] += trade.shares
            elif outcome == "down":
                pos.down_shares += trade.shares
                pos.down_cost += trade.usdc
                self._down_shares_bought[wallet][market] += trade.shares

        else:  # SELL
            if outcome == "up":
                pos.up_shares -= trade.shares
                pos.up_revenue += trade.usdc
            elif outcome == "down":
                pos.down_shares -= trade.shares
                pos.down_revenue += trade.usdc

        # Recalculate derived metrics
        self._recalculate_metrics(pos, wallet, market)

        return pos

    def _recalculate_metrics(self, pos: WalletPosition, wallet: str, market: str):
        """Recalculate derived position metrics."""
        # Ensure non-negative (can go negative with sells)
        pos.up_shares = max(0, pos.up_shares)
        pos.down_shares = max(0, pos.down_shares)

        # Complete sets = min of up and down shares
        pos.complete_sets = min(pos.up_shares, pos.down_shares)

        # Unhedged positions
        pos.unhedged_up = max(0, pos.up_shares - pos.down_shares)
        pos.unhedged_down = max(0, pos.down_shares - pos.up_shares)

        # Average prices (based on total cost / total shares bought, not net)
        up_bought = self._up_shares_bought[wallet][market]
        down_bought = self._down_shares_bought[wallet][market]

        pos.avg_up_price = pos.up_cost / up_bought if up_bought > 0 else 0
        pos.avg_down_price = pos.down_cost / down_bought if down_bought > 0 else 0

        # Combined price (edge indicator)
        if up_bought > 0 and down_bought > 0:
            pos.combined_price = pos.avg_up_price + pos.avg_down_price
            pos.edge = 1.0 - pos.combined_price
        else:
            pos.combined_price = 0
            pos.edge = 0

        # Hedge ratio
        if pos.up_shares > 0 and pos.down_shares > 0:
            pos.hedge_ratio = min(pos.up_shares, pos.down_shares) / max(pos.up_shares, pos.down_shares)
        elif pos.up_shares > 0 or pos.down_shares > 0:
            pos.hedge_ratio = 0
        else:
            pos.hedge_ratio = 1.0  # No position = perfectly hedged

    def get_position(self, wallet: str, market_slug: str) -> WalletPosition:
        """Get position for a specific wallet and market."""
        wallet = wallet.lower()
        return self.positions.get(wallet, {}).get(market_slug)

    def get_wallet_positions(self, wallet: str) -> List[WalletPosition]:
        """Get all positions for a specific wallet."""
        wallet = wallet.lower()
        return list(self.positions.get(wallet, {}).values())

    def get_market_positions(self, market_slug: str) -> List[WalletPosition]:
        """Get all positions for a specific market."""
        positions = []
        for wallet_positions in self.positions.values():
            if market_slug in wallet_positions:
                positions.append(wallet_positions[market_slug])
        return positions

    def get_all_positions(self) -> List[WalletPosition]:
        """Get all current positions."""
        positions = []
        for wallet_positions in self.positions.values():
            positions.extend(wallet_positions.values())
        return positions

    def get_active_markets(self) -> List[str]:
        """Get list of all markets with positions."""
        markets = set()
        for wallet_positions in self.positions.values():
            markets.update(wallet_positions.keys())
        return list(markets)

    def get_summary(self) -> dict:
        """Get summary statistics."""
        all_positions = self.get_all_positions()
        total_trades = sum(p.total_trades for p in all_positions)

        return {
            "total_wallets": len(self.positions),
            "total_markets": len(self.get_active_markets()),
            "total_positions": len(all_positions),
            "total_trades": total_trades,
        }

    def cleanup_resolved_markets(self, resolved_slugs: List[str]):
        """Remove positions for resolved markets to prevent memory bloat."""
        removed_count = 0
        for wallet in list(self.positions.keys()):
            for slug in resolved_slugs:
                if slug in self.positions[wallet]:
                    del self.positions[wallet][slug]
                    removed_count += 1
                self._up_shares_bought[wallet].pop(slug, None)
                self._down_shares_bought[wallet].pop(slug, None)

        if removed_count:
            print(f"[PositionTracker] Cleaned up {removed_count} positions")
