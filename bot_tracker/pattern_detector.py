"""
Pattern detector - analyzes timing, price, and hedging patterns.
"""

from typing import Dict, List, Optional
from collections import defaultdict

from .models import (
    TradeEvent,
    WalletPosition,
    MarketContext,
    TimingPattern,
    PricePattern,
    HedgePattern
)
from .config import TARGET_WALLETS


class PatternDetector:
    """Detects and analyzes trading patterns for bot wallets."""

    def __init__(self):
        # trade_history[wallet][market_slug] = List[TradeEvent]
        self.trade_history: Dict[str, Dict[str, List[TradeEvent]]] = defaultdict(lambda: defaultdict(list))

    def record_trade(self, trade: TradeEvent):
        """Record a trade for pattern analysis (keeps last 100 per wallet/market)."""
        wallet = trade.wallet.lower()
        market = trade.market_slug
        self.trade_history[wallet][market].append(trade)
        # Limit memory: keep last 100 trades per wallet/market
        if len(self.trade_history[wallet][market]) > 100:
            self.trade_history[wallet][market] = self.trade_history[wallet][market][-100:]

    def get_trades(self, wallet: str, market_slug: str) -> List[TradeEvent]:
        """Get all trades for a wallet in a market."""
        return self.trade_history.get(wallet.lower(), {}).get(market_slug, [])

    def analyze_timing(
        self,
        wallet: str,
        market_slug: str,
        market_context: Optional[MarketContext] = None
    ) -> Optional[TimingPattern]:
        """Analyze timing patterns for a wallet in a market."""
        wallet = wallet.lower()
        trades = self.get_trades(wallet, market_slug)

        if not trades:
            return None

        wallet_name = TARGET_WALLETS.get(wallet, wallet[:10])

        # Get trade timestamps
        timestamps = [t.timestamp for t in trades]
        first_ts = min(timestamps)
        last_ts = max(timestamps)

        # Calculate trading window
        trading_window_mins = (last_ts - first_ts) / 60 if last_ts > first_ts else 0
        trades_per_minute = len(trades) / trading_window_mins if trading_window_mins > 0 else len(trades)

        # Calculate timing relative to market
        time_to_start_mins = 0
        time_to_end_mins = 0
        early_trader = False
        late_closer = False

        if market_context and market_context.start_date and market_context.end_date:
            market_start_ts = market_context.start_date.timestamp()
            market_end_ts = market_context.end_date.timestamp()

            time_to_start_mins = (first_ts - market_start_ts) / 60
            time_to_end_mins = (market_end_ts - last_ts) / 60

            early_trader = time_to_start_mins < 2  # Within 2 minutes of market open
            late_closer = time_to_end_mins < 2  # Within 2 minutes of market close

        return TimingPattern(
            wallet=wallet,
            wallet_name=wallet_name,
            market_slug=market_slug,
            time_to_start_mins=time_to_start_mins,
            time_to_end_mins=time_to_end_mins,
            trading_window_mins=trading_window_mins,
            trades_per_minute=trades_per_minute,
            early_trader=early_trader,
            late_closer=late_closer
        )

    def analyze_price(
        self,
        wallet: str,
        market_slug: str
    ) -> Optional[PricePattern]:
        """Analyze price strategy for a wallet in a market."""
        wallet = wallet.lower()
        trades = self.get_trades(wallet, market_slug)

        if not trades:
            return None

        wallet_name = TARGET_WALLETS.get(wallet, wallet[:10])

        # Separate trades by outcome and side
        up_buys = [t for t in trades if t.outcome.lower() == "up" and t.side == "BUY"]
        down_buys = [t for t in trades if t.outcome.lower() == "down" and t.side == "BUY"]
        up_sells = [t for t in trades if t.outcome.lower() == "up" and t.side == "SELL"]
        down_sells = [t for t in trades if t.outcome.lower() == "down" and t.side == "SELL"]

        # Calculate weighted average prices
        def weighted_avg(trades: List[TradeEvent]) -> float:
            if not trades:
                return 0
            total_shares = sum(t.shares for t in trades)
            if total_shares == 0:
                return 0
            return sum(t.price * t.shares for t in trades) / total_shares

        avg_buy_up = weighted_avg(up_buys)
        avg_buy_down = weighted_avg(down_buys)
        avg_sell_up = weighted_avg(up_sells)
        avg_sell_down = weighted_avg(down_sells)

        combined_buy_price = 0
        if avg_buy_up > 0 and avg_buy_down > 0:
            combined_buy_price = avg_buy_up + avg_buy_down

        # Spread captured (profit potential per share)
        spread_captured = 0
        if avg_sell_up > 0 and avg_buy_up > 0:
            spread_captured += (avg_sell_up - avg_buy_up)
        if avg_sell_down > 0 and avg_buy_down > 0:
            spread_captured += (avg_sell_down - avg_buy_down)

        # Maker percentage
        maker_trades = sum(1 for t in trades if t.role == "maker")
        maker_percentage = maker_trades / len(trades) if trades else 0

        # Check if buying below $1 combined (arbitrage signal)
        bought_below_dollar = combined_buy_price < 1.0 if combined_buy_price > 0 else False

        return PricePattern(
            wallet=wallet,
            wallet_name=wallet_name,
            market_slug=market_slug,
            avg_buy_price_up=avg_buy_up,
            avg_buy_price_down=avg_buy_down,
            avg_sell_price_up=avg_sell_up,
            avg_sell_price_down=avg_sell_down,
            combined_buy_price=combined_buy_price,
            spread_captured=spread_captured,
            bought_below_dollar=bought_below_dollar,
            maker_percentage=maker_percentage
        )

    def analyze_hedge(
        self,
        position: WalletPosition
    ) -> Optional[HedgePattern]:
        """Analyze hedging behavior based on position."""
        if not position:
            return None

        # Determine dominant side
        if position.up_shares == 0 and position.down_shares == 0:
            dominant = "BALANCED"
        elif position.up_shares > position.down_shares * 1.5:
            dominant = "UP"
        elif position.down_shares > position.up_shares * 1.5:
            dominant = "DOWN"
        else:
            dominant = "BALANCED"

        # Determine strategy type
        if position.hedge_ratio > 0.9 and position.edge > 0:
            strategy_type = "ARBITRAGE"  # Highly hedged with positive edge
        elif position.hedge_ratio > 0.7:
            strategy_type = "MARKET_MAKING"  # Moderately hedged
        elif position.hedge_ratio < 0.3:
            strategy_type = "DIRECTIONAL"  # Taking a side
        else:
            strategy_type = "MIXED"

        return HedgePattern(
            wallet=position.wallet,
            wallet_name=position.wallet_name,
            market_slug=position.market_slug,
            hedge_ratio=position.hedge_ratio,
            up_shares=position.up_shares,
            down_shares=position.down_shares,
            is_fully_hedged=position.hedge_ratio > 0.95,
            is_directional=position.hedge_ratio < 0.3,
            dominant_side=dominant,
            strategy_type=strategy_type
        )

    def get_full_analysis(
        self,
        wallet: str,
        market_slug: str,
        position: Optional[WalletPosition] = None,
        market_context: Optional[MarketContext] = None
    ) -> dict:
        """Get complete pattern analysis for a wallet in a market."""
        timing = self.analyze_timing(wallet, market_slug, market_context)
        price = self.analyze_price(wallet, market_slug)
        hedge = self.analyze_hedge(position) if position else None

        return {
            "timing": timing.model_dump() if timing else None,
            "price": price.model_dump() if price else None,
            "hedge": hedge.model_dump() if hedge else None
        }

    def get_all_patterns(
        self,
        positions: Dict[str, WalletPosition],
        market_contexts: Dict[str, MarketContext]
    ) -> Dict[str, dict]:
        """Get patterns for all tracked wallet/market combinations."""
        patterns = {}

        for wallet in self.trade_history:
            for market_slug in self.trade_history[wallet]:
                key = f"{wallet}:{market_slug}"
                position = positions.get(key)
                market = market_contexts.get(market_slug)

                patterns[key] = self.get_full_analysis(
                    wallet, market_slug, position, market
                )

        return patterns

    def get_summary_stats(self) -> dict:
        """Get summary statistics across all trades."""
        total_trades = 0
        total_wallets = len(self.trade_history)
        total_markets = set()

        for wallet in self.trade_history:
            for market_slug, trades in self.trade_history[wallet].items():
                total_trades += len(trades)
                total_markets.add(market_slug)

        return {
            "total_trades": total_trades,
            "total_wallets": total_wallets,
            "total_markets": len(total_markets)
        }
