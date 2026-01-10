"""
Rank traders and compute bot-likelihood scores.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .trade_aggregator import TraderMetrics
from .config import BOT_SCORE_THRESHOLDS


@dataclass
class RankedTrader:
    """A trader with rankings and bot score."""
    wallet: str
    metrics: TraderMetrics

    # Rankings
    rank_by_volume: int = 0
    rank_by_trades: int = 0
    rank_by_pnl: int = 0

    # Bot analysis
    bot_score: float = 0.0
    bot_indicators: List[str] = field(default_factory=list)

    # Historical P&L
    pnl_all_time: Optional[float] = None
    pnl_1d: Optional[float] = None
    pnl_1w: Optional[float] = None
    pnl_1m: Optional[float] = None

    @property
    def short_wallet(self) -> str:
        """Shortened wallet address for display."""
        if len(self.wallet) > 10:
            return f"{self.wallet[:6]}...{self.wallet[-4:]}"
        return self.wallet

    @property
    def profile_url(self) -> str:
        """Polymarket profile URL."""
        return f"https://polymarket.com/profile/{self.wallet}"


def compute_bot_score(metrics: TraderMetrics) -> tuple[float, List[str]]:
    """
    Compute a 0-100 score indicating likelihood of being a bot.

    Returns (score, list of indicators).

    Bot-like characteristics:
    1. High maker ratio (>70%) - Bots place limit orders
    2. High trade count (>100 in markets analyzed)
    3. Balanced positions (arbitrage bots buy both sides)
    4. Fast trading (many trades in short duration)
    5. Consistent profitability
    """
    score = 0.0
    indicators = []

    # 1. High maker ratio (+20 points)
    if metrics.maker_ratio > BOT_SCORE_THRESHOLDS["high_maker_ratio"]:
        score += 20
        indicators.append(f"High maker ratio ({metrics.maker_ratio:.0%})")
    elif metrics.maker_ratio > 0.5:
        score += 10

    # 2. High trade count (+25 points max)
    threshold = BOT_SCORE_THRESHOLDS["high_trade_count"]
    if metrics.total_trades > threshold * 5:
        score += 25
        indicators.append(f"Very high trade frequency ({metrics.total_trades:,} trades)")
    elif metrics.total_trades > threshold:
        score += 15
        indicators.append(f"High trade frequency ({metrics.total_trades:,} trades)")
    elif metrics.total_trades > threshold / 2:
        score += 10

    # 3. Balanced positions - arbitrage signal (+20 points)
    balance_threshold = BOT_SCORE_THRESHOLDS["balanced_positions"]
    if metrics.position_balance_ratio > balance_threshold:
        score += 20
        indicators.append(f"Balanced positions (arbitrage pattern, ratio {metrics.position_balance_ratio:.2f})")
    elif metrics.position_balance_ratio > 0.6:
        score += 10
        indicators.append(f"Somewhat balanced positions (ratio {metrics.position_balance_ratio:.2f})")

    # 4. Fast trading (+20 points)
    trades_per_min_threshold = BOT_SCORE_THRESHOLDS["fast_trading"]
    if metrics.trades_per_minute > trades_per_min_threshold:
        score += 20
        indicators.append(f"Fast trading ({metrics.trades_per_minute:.1f} trades/min)")
    elif metrics.trades_per_minute > trades_per_min_threshold / 2:
        score += 10

    # 5. Profitability (+15 points)
    if metrics.realized_pnl is not None:
        if metrics.realized_pnl > 100:
            score += 15
            indicators.append(f"Profitable (+${metrics.realized_pnl:,.2f})")
        elif metrics.realized_pnl > 0:
            score += 10
            indicators.append(f"Slightly profitable (+${metrics.realized_pnl:,.2f})")

    # 6. Multiple markets traded bonus (+5 points)
    if metrics.markets_traded > 3:
        score += 5
        indicators.append(f"Active across {metrics.markets_traded} markets")

    # 7. Edge capture (arbitrage success) (+10 points)
    if metrics.edge > 0.02:  # > 2% edge
        score += 10
        indicators.append(f"Captured {metrics.edge:.1%} edge")

    return min(score, 100), indicators


def rank_traders(traders: Dict[str, TraderMetrics]) -> List[RankedTrader]:
    """
    Rank traders by multiple criteria and compute bot scores.

    Returns list of RankedTrader sorted by volume (descending).
    """
    # Convert to list for ranking
    trader_list = list(traders.values())

    # Sort by different metrics to get rankings
    by_volume = sorted(trader_list, key=lambda t: t.total_volume_usdc, reverse=True)
    by_trades = sorted(trader_list, key=lambda t: t.total_trades, reverse=True)
    by_pnl = sorted(
        trader_list,
        key=lambda t: t.realized_pnl if t.realized_pnl is not None else float('-inf'),
        reverse=True
    )

    # Create ranking maps
    volume_rank = {t.wallet: i + 1 for i, t in enumerate(by_volume)}
    trades_rank = {t.wallet: i + 1 for i, t in enumerate(by_trades)}
    pnl_rank = {t.wallet: i + 1 for i, t in enumerate(by_pnl)}

    # Create RankedTrader objects
    ranked = []
    for metrics in trader_list:
        bot_score, bot_indicators = compute_bot_score(metrics)

        ranked.append(RankedTrader(
            wallet=metrics.wallet,
            metrics=metrics,
            rank_by_volume=volume_rank[metrics.wallet],
            rank_by_trades=trades_rank[metrics.wallet],
            rank_by_pnl=pnl_rank[metrics.wallet],
            bot_score=bot_score,
            bot_indicators=bot_indicators
        ))

    # Sort by volume for output
    ranked.sort(key=lambda r: r.metrics.total_volume_usdc, reverse=True)

    return ranked


def get_likely_bots(ranked: List[RankedTrader], threshold: float = 70.0) -> List[RankedTrader]:
    """
    Filter traders likely to be bots (score >= threshold).
    """
    return [r for r in ranked if r.bot_score >= threshold]


def format_trader_table(
    ranked: List[RankedTrader],
    limit: int = 20
) -> str:
    """
    Format ranked traders as a text table.
    """
    lines = []
    header = "Rank | Wallet         | Volume      | Trades | Maker% | P&L       | Bot Score"
    separator = "-----+----------------+-------------+--------+--------+-----------+----------"
    lines.append(header)
    lines.append(separator)

    for i, r in enumerate(ranked[:limit], 1):
        pnl_str = f"+${r.metrics.realized_pnl:,.0f}" if r.metrics.realized_pnl and r.metrics.realized_pnl > 0 else \
                  f"-${abs(r.metrics.realized_pnl):,.0f}" if r.metrics.realized_pnl and r.metrics.realized_pnl < 0 else \
                  "N/A"

        lines.append(
            f"{i:>4} | {r.short_wallet:<14} | ${r.metrics.total_volume_usdc:>9,.0f} | "
            f"{r.metrics.total_trades:>6,} | {r.metrics.maker_ratio:>5.0%} | "
            f"{pnl_str:>9} | {r.bot_score:>8.0f}"
        )

    return "\n".join(lines)


def format_bot_details(ranked: List[RankedTrader], limit: int = 10) -> str:
    """
    Format detailed bot analysis for top likely bots.
    """
    bots = get_likely_bots(ranked)
    if not bots:
        return "No likely bots identified (score >= 70)"

    lines = [f"Total identified: {len(bots)} wallets\n"]

    for i, bot in enumerate(bots[:limit], 1):
        pnl_str = f"+${bot.metrics.realized_pnl:,.2f}" if bot.metrics.realized_pnl and bot.metrics.realized_pnl > 0 else \
                  f"-${abs(bot.metrics.realized_pnl):,.2f}" if bot.metrics.realized_pnl and bot.metrics.realized_pnl < 0 else \
                  "N/A"

        lines.append(f"{i}. {bot.short_wallet} (Bot Score: {bot.bot_score:.0f})")
        lines.append(f"   Volume: ${bot.metrics.total_volume_usdc:,.0f} | Trades: {bot.metrics.total_trades:,} | P&L: {pnl_str}")
        lines.append(f"   Indicators:")
        for indicator in bot.bot_indicators:
            lines.append(f"   - {indicator}")
        lines.append(f"   Profile: {bot.profile_url}")
        lines.append("")

    return "\n".join(lines)


def _format_pnl(pnl: Optional[float]) -> str:
    """Format P&L value for display."""
    if pnl is None:
        return "N/A"
    if pnl >= 0:
        if pnl >= 1000000:
            return f"+${pnl/1e6:.1f}M"
        elif pnl >= 1000:
            return f"+${pnl/1e3:.0f}K"
        else:
            return f"+${pnl:.0f}"
    else:
        abs_pnl = abs(pnl)
        if abs_pnl >= 1000000:
            return f"-${abs_pnl/1e6:.1f}M"
        elif abs_pnl >= 1000:
            return f"-${abs_pnl/1e3:.0f}K"
        else:
            return f"-${abs_pnl:.0f}"


def format_trader_table_with_profiles(
    ranked: List[RankedTrader],
    profiles: dict,
    limit: int = 20
) -> str:
    """
    Format ranked traders as a text table with usernames and historical P&L.
    """
    lines = []
    header = "Rank | Username         | Volume      | P&L(Ses)  | P&L(All)   | Trades | Bot"
    separator = "-----+------------------+-------------+-----------+------------+--------+----"
    lines.append(header)
    lines.append(separator)

    for i, r in enumerate(ranked[:limit], 1):
        session_pnl = _format_pnl(r.metrics.realized_pnl)
        alltime_pnl = _format_pnl(r.pnl_all_time)

        # Get username from profile
        profile = profiles.get(r.wallet.lower())
        username = f"@{profile.username}" if profile and profile.username else r.short_wallet

        lines.append(
            f"{i:>4} | {username:<16} | ${r.metrics.total_volume_usdc:>9,.0f} | "
            f"{session_pnl:>9} | {alltime_pnl:>10} | "
            f"{r.metrics.total_trades:>6,} | {r.bot_score:>3.0f}"
        )

    return "\n".join(lines)


def format_bot_details_with_profiles(
    ranked: List[RankedTrader],
    profiles: dict,
    limit: int = 10
) -> str:
    """
    Format detailed bot analysis with usernames and historical P&L.
    """
    bots = get_likely_bots(ranked)
    if not bots:
        return "No likely bots identified (score >= 70)"

    lines = [f"Total identified: {len(bots)} wallets\n"]

    for i, bot in enumerate(bots[:limit], 1):
        session_pnl = _format_pnl(bot.metrics.realized_pnl)

        # Get username from profile
        profile = profiles.get(bot.wallet.lower())
        username = f"@{profile.username}" if profile and profile.username else bot.short_wallet

        lines.append(f"{i}. {username} (Bot Score: {bot.bot_score:.0f})")
        lines.append(f"   Wallet: {bot.wallet}")
        lines.append(f"   Volume: ${bot.metrics.total_volume_usdc:,.0f} | Trades: {bot.metrics.total_trades:,} | Session P&L: {session_pnl}")

        # Historical P&L
        alltime = _format_pnl(bot.pnl_all_time)
        pnl_1d = _format_pnl(bot.pnl_1d)
        pnl_1w = _format_pnl(bot.pnl_1w)
        pnl_1m = _format_pnl(bot.pnl_1m)
        lines.append(f"   Historical P&L: 1d={pnl_1d} | 1w={pnl_1w} | 1m={pnl_1m} | All={alltime}")

        lines.append(f"   Indicators:")
        for indicator in bot.bot_indicators:
            lines.append(f"   - {indicator}")
        lines.append(f"   Profile: {bot.profile_url}")
        lines.append("")

    return "\n".join(lines)
