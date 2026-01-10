#!/usr/bin/env python3
"""
Deep Strategy Analysis for Target Bot Wallets

Analyzes 5 highly profitable bot traders across 6 BTC/ETH Up/Down markets
to understand their trading strategies in detail.

Usage:
    python analyze_target_wallets.py           # Run full analysis
    python analyze_target_wallets.py --fetch   # Only fetch data
    python analyze_target_wallets.py --report  # Generate reports from cached data
"""

import json
import time
import sys
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot_identifier.config import RATE_LIMIT_DELAY
from bot_identifier.market_fetcher import (
    fetch_market_metadata,
    fetch_and_parse_market_trades,
    MarketMetadata,
    ParsedTrade
)
from bot_identifier.trade_aggregator import (
    aggregate_trades,
    calculate_pnl,
    TraderMetrics
)

# ============================================================================
# CONFIGURATION
# ============================================================================

TARGET_WALLETS = [
    "0x589222a5124a96765443b97a3498d89ffd824ad2",
    "0x0ea574f3204c5c9c0cdead90392ea0990f4d17e4",
    "0xd0d6053c3c37e727402d84c14069780d360993aa",
    "0x63ce342161250d705dc0b16df89036c8e5f9ba9a",
]

MARKETS = [
    {"slug": "eth-updown-15m-1768037400", "winning_outcome": "up"},
    {"slug": "eth-updown-15m-1768036500", "winning_outcome": "up"},
    {"slug": "btc-updown-15m-1768037400", "winning_outcome": "up"},
    {"slug": "btc-updown-15m-1768036500", "winning_outcome": "up"},
    {"slug": "eth-updown-15m-1768035600", "winning_outcome": "down"},
    {"slug": "btc-updown-15m-1768034700", "winning_outcome": "up"},
]

OUTPUT_DIR = Path(__file__).parent / "output"

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class WalletMarketAnalysis:
    """Analysis of a single wallet in a single market."""
    wallet: str
    market_slug: str
    market_question: str
    winning_outcome: str

    # Trade counts
    total_trades: int = 0
    maker_trades: int = 0
    taker_trades: int = 0

    # Positions
    up_bought: float = 0.0
    down_bought: float = 0.0
    up_sold: float = 0.0
    down_sold: float = 0.0
    up_cost: float = 0.0      # USDC spent buying Up
    down_cost: float = 0.0    # USDC spent buying Down
    up_revenue: float = 0.0   # USDC received selling Up
    down_revenue: float = 0.0 # USDC received selling Down

    # Timing (unix timestamps)
    first_trade_ts: int = 0
    last_trade_ts: int = 0
    market_start_ts: int = 0
    market_end_ts: int = 0

    # P&L
    realized_pnl: float = 0.0

    # Order sizes
    order_sizes: List[float] = field(default_factory=list)

    # Trade intervals (seconds between consecutive trades)
    trade_intervals: List[float] = field(default_factory=list)

    # Prices
    up_prices: List[float] = field(default_factory=list)
    down_prices: List[float] = field(default_factory=list)

    @property
    def maker_ratio(self) -> float:
        return self.maker_trades / self.total_trades if self.total_trades > 0 else 0

    @property
    def up_net(self) -> float:
        return self.up_bought - self.up_sold

    @property
    def down_net(self) -> float:
        return self.down_bought - self.down_sold

    @property
    def position_balance(self) -> float:
        """Ratio of smaller to larger position. 1.0 = perfect balance."""
        up = abs(self.up_net)
        down = abs(self.down_net)
        if up == 0 and down == 0:
            return 0.0
        if up == 0 or down == 0:
            return 0.0
        return min(up, down) / max(up, down)

    @property
    def avg_up_price(self) -> float:
        return self.up_cost / self.up_bought if self.up_bought > 0 else 0

    @property
    def avg_down_price(self) -> float:
        return self.down_cost / self.down_bought if self.down_bought > 0 else 0

    @property
    def combined_price(self) -> float:
        """Combined cost of Up + Down. < 1.0 means arbitrage opportunity."""
        if self.avg_up_price > 0 and self.avg_down_price > 0:
            return self.avg_up_price + self.avg_down_price
        return 0

    @property
    def edge(self) -> float:
        """Arbitrage edge: 1 - combined_price."""
        if self.combined_price > 0:
            return 1.0 - self.combined_price
        return 0

    @property
    def complete_sets(self) -> float:
        """Number of complete Up/Down pairs."""
        return min(self.up_net, self.down_net) if self.up_net > 0 and self.down_net > 0 else 0

    @property
    def trading_duration_secs(self) -> float:
        return self.last_trade_ts - self.first_trade_ts if self.last_trade_ts > self.first_trade_ts else 0

    @property
    def trades_per_minute(self) -> float:
        duration_mins = self.trading_duration_secs / 60
        return self.total_trades / duration_mins if duration_mins > 0 else 0

    @property
    def avg_order_size(self) -> float:
        return sum(self.order_sizes) / len(self.order_sizes) if self.order_sizes else 0

    @property
    def avg_trade_interval(self) -> float:
        return sum(self.trade_intervals) / len(self.trade_intervals) if self.trade_intervals else 0

    @property
    def entry_delay_secs(self) -> float:
        """Seconds after market open before first trade."""
        if self.first_trade_ts > 0 and self.market_start_ts > 0:
            return max(0, self.first_trade_ts - self.market_start_ts)
        return 0

    @property
    def exit_buffer_secs(self) -> float:
        """Seconds before market close of last trade."""
        if self.last_trade_ts > 0 and self.market_end_ts > 0:
            return max(0, self.market_end_ts - self.last_trade_ts)
        return 0


@dataclass
class WalletStrategyFingerprint:
    """Strategy fingerprint for a wallet across all markets."""
    wallet: str
    short_wallet: str

    # Aggregate metrics
    total_trades: int = 0
    total_pnl: float = 0.0
    markets_traded: int = 0

    # Averages across markets
    avg_maker_ratio: float = 0.0
    avg_order_size: float = 0.0
    avg_trades_per_minute: float = 0.0
    avg_position_balance: float = 0.0
    avg_edge: float = 0.0
    avg_entry_delay_secs: float = 0.0
    avg_exit_buffer_secs: float = 0.0
    avg_trade_interval_secs: float = 0.0

    # Strategy classification
    strategy_type: str = ""  # "arbitrage", "directional", "mixed"

    # Bot indicators
    bot_indicators: List[str] = field(default_factory=list)


# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_all_market_data() -> Tuple[List[MarketMetadata], Dict[str, List[ParsedTrade]]]:
    """
    Fetch metadata and all trades for configured markets.
    Returns (markets, {market_slug: [trades]})
    """
    print("\n" + "=" * 70)
    print("PHASE 1: FETCHING MARKET DATA")
    print("=" * 70)

    markets = []
    all_trades = {}

    for i, market_config in enumerate(MARKETS, 1):
        slug = market_config["slug"]
        print(f"\n[{i}/{len(MARKETS)}] {slug}")

        # Fetch metadata
        print("  Fetching metadata...", end=" ")
        metadata = fetch_market_metadata(slug)
        if not metadata:
            print("FAILED")
            continue

        # Override winning outcome from our config (more reliable)
        metadata.winning_outcome = market_config["winning_outcome"]
        metadata.resolved = True
        markets.append(metadata)
        print(f"OK - {metadata.question[:50]}...")

        time.sleep(RATE_LIMIT_DELAY)

        # Fetch all trades
        print("  Fetching trades...", end=" ")
        trades = fetch_and_parse_market_trades(metadata)
        all_trades[slug] = trades
        print(f"{len(trades)} trades")

        time.sleep(RATE_LIMIT_DELAY)

    print(f"\nTotal: {len(markets)} markets, {sum(len(t) for t in all_trades.values())} trades")
    return markets, all_trades


def filter_target_wallet_trades(
    all_trades: Dict[str, List[ParsedTrade]]
) -> Dict[str, Dict[str, List[ParsedTrade]]]:
    """
    Filter trades to only target wallets.
    Returns {wallet: {market_slug: [trades]}}
    """
    print("\n" + "=" * 70)
    print("PHASE 2: FILTERING TARGET WALLET TRADES")
    print("=" * 70)

    target_set = set(w.lower() for w in TARGET_WALLETS)
    result = {w.lower(): {} for w in TARGET_WALLETS}

    for market_slug, trades in all_trades.items():
        for trade in trades:
            wallet = trade.wallet.lower()
            if wallet in target_set:
                if market_slug not in result[wallet]:
                    result[wallet][market_slug] = []
                result[wallet][market_slug].append(trade)

    # Print summary
    for wallet in TARGET_WALLETS:
        w = wallet.lower()
        total = sum(len(trades) for trades in result[w].values())
        markets = len(result[w])
        print(f"  {wallet[:10]}... : {total} trades across {markets} markets")

    return result


# ============================================================================
# ANALYSIS
# ============================================================================

def analyze_wallet_market(
    wallet: str,
    market: MarketMetadata,
    trades: List[ParsedTrade]
) -> WalletMarketAnalysis:
    """Analyze a single wallet's activity in a single market."""

    analysis = WalletMarketAnalysis(
        wallet=wallet,
        market_slug=market.slug,
        market_question=market.question,
        winning_outcome=market.winning_outcome or ""
    )

    if not trades:
        return analysis

    # Sort trades by timestamp
    trades = sorted(trades, key=lambda t: t.timestamp)

    # Parse market times from metadata
    if market.start_date:
        try:
            from bot_identifier.market_fetcher import parse_iso_datetime
            start_dt = parse_iso_datetime(market.start_date)
            analysis.market_start_ts = int(start_dt.timestamp())
        except:
            pass

    if market.end_date:
        try:
            from bot_identifier.market_fetcher import parse_iso_datetime
            end_dt = parse_iso_datetime(market.end_date)
            analysis.market_end_ts = int(end_dt.timestamp())
        except:
            pass

    prev_ts = None

    for trade in trades:
        analysis.total_trades += 1

        if trade.role == "maker":
            analysis.maker_trades += 1
        else:
            analysis.taker_trades += 1

        # Positions, costs, and revenue
        if trade.side == "BUY":
            if trade.outcome.lower() == "up":
                analysis.up_bought += trade.shares
                analysis.up_cost += trade.usdc
                analysis.up_prices.append(trade.price)
            else:
                analysis.down_bought += trade.shares
                analysis.down_cost += trade.usdc
                analysis.down_prices.append(trade.price)
        else:  # SELL
            if trade.outcome.lower() == "up":
                analysis.up_sold += trade.shares
                analysis.up_revenue += trade.usdc
            else:
                analysis.down_sold += trade.shares
                analysis.down_revenue += trade.usdc

        # Order sizes
        analysis.order_sizes.append(trade.shares)

        # Timestamps
        if analysis.first_trade_ts == 0:
            analysis.first_trade_ts = trade.timestamp
        analysis.last_trade_ts = trade.timestamp

        # Trade intervals
        if prev_ts is not None:
            interval = trade.timestamp - prev_ts
            if interval > 0:
                analysis.trade_intervals.append(interval)
        prev_ts = trade.timestamp

    # Calculate P&L
    #
    # IMPORTANT: CLOB data doesn't capture minting (pay $1 → get 1 Up + 1 Down).
    # If net position is negative (sold more than bought), those shares came from minting.
    #
    # P&L calculation:
    # 1. Resolution payout: Only POSITIVE net positions get paid ($1 if wins, $0 if loses)
    # 2. Implied minting: If we sold shares we didn't buy, we must have minted them
    #    - Minting cost = $1 per complete set
    #    - We infer minted sets from min(up_sold_excess, down_position) or similar
    # 3. CLOB activity: buy costs and sell revenues
    #
    # Simplified approach:
    # - Positive net position → you hold shares, get resolution payout
    # - Negative net position → you sold minted shares, already got revenue, no further payout/liability

    if market.winning_outcome:
        winning = market.winning_outcome.lower()

        # Only positive positions get resolution payout
        up_payout = max(0, analysis.up_net) * (1.0 if winning == "up" else 0.0)
        down_payout = max(0, analysis.down_net) * (1.0 if winning == "down" else 0.0)
        resolution_payout = up_payout + down_payout

        # Calculate implied minting cost
        # If we sold more than we bought, we must have minted
        up_sold_excess = max(0, analysis.up_sold - analysis.up_bought)
        down_sold_excess = max(0, analysis.down_sold - analysis.down_bought)
        # Minting gives BOTH Up and Down, so minted sets = min of the two excesses
        # But if one side has excess and other doesn't, they still minted for that side
        # Actually: each minted set gives 1 Up + 1 Down for $1
        # If we have excess Up sold, we minted at least that many sets
        # If we have excess Down sold, we minted at least that many sets
        # The max represents the minimum minting needed
        implied_minted_sets = max(up_sold_excess, down_sold_excess)
        minting_cost = implied_minted_sets * 1.0  # $1 per complete set

        total_revenue = analysis.up_revenue + analysis.down_revenue
        total_cost = analysis.up_cost + analysis.down_cost + minting_cost

        analysis.realized_pnl = resolution_payout + total_revenue - total_cost

    return analysis


def analyze_all_wallets(
    markets: List[MarketMetadata],
    wallet_trades: Dict[str, Dict[str, List[ParsedTrade]]]
) -> Dict[str, List[WalletMarketAnalysis]]:
    """
    Analyze all target wallets across all markets.
    Returns {wallet: [WalletMarketAnalysis per market]}
    """
    print("\n" + "=" * 70)
    print("PHASE 3: ANALYZING WALLET STRATEGIES")
    print("=" * 70)

    market_by_slug = {m.slug: m for m in markets}
    results = {}

    for wallet in TARGET_WALLETS:
        w = wallet.lower()
        results[w] = []

        print(f"\n  Analyzing {wallet[:10]}...")

        for market in markets:
            trades = wallet_trades.get(w, {}).get(market.slug, [])
            if trades:
                analysis = analyze_wallet_market(w, market, trades)
                results[w].append(analysis)
                print(f"    {market.slug}: {analysis.total_trades} trades, "
                      f"edge={analysis.edge:.2%}, P&L=${analysis.realized_pnl:.2f}")

    return results


def create_strategy_fingerprints(
    wallet_analyses: Dict[str, List[WalletMarketAnalysis]]
) -> List[WalletStrategyFingerprint]:
    """Create strategy fingerprints for each wallet."""

    fingerprints = []

    for wallet, analyses in wallet_analyses.items():
        if not analyses:
            continue

        fp = WalletStrategyFingerprint(
            wallet=wallet,
            short_wallet=f"{wallet[:6]}...{wallet[-4:]}"
        )

        # Aggregate across markets
        fp.markets_traded = len(analyses)
        fp.total_trades = sum(a.total_trades for a in analyses)
        fp.total_pnl = sum(a.realized_pnl for a in analyses)

        # Averages
        if analyses:
            fp.avg_maker_ratio = sum(a.maker_ratio for a in analyses) / len(analyses)
            fp.avg_order_size = sum(a.avg_order_size for a in analyses) / len(analyses)
            fp.avg_trades_per_minute = sum(a.trades_per_minute for a in analyses) / len(analyses)
            fp.avg_position_balance = sum(a.position_balance for a in analyses) / len(analyses)
            fp.avg_edge = sum(a.edge for a in analyses if a.edge > 0) / max(1, sum(1 for a in analyses if a.edge > 0))
            fp.avg_entry_delay_secs = sum(a.entry_delay_secs for a in analyses) / len(analyses)
            fp.avg_exit_buffer_secs = sum(a.exit_buffer_secs for a in analyses) / len(analyses)
            fp.avg_trade_interval_secs = sum(a.avg_trade_interval for a in analyses) / len(analyses)

        # Strategy classification
        if fp.avg_position_balance > 0.8:
            fp.strategy_type = "arbitrage"
        elif fp.avg_position_balance < 0.3:
            fp.strategy_type = "directional"
        else:
            fp.strategy_type = "mixed"

        # Bot indicators
        if fp.avg_maker_ratio > 0.7:
            fp.bot_indicators.append(f"High maker ratio ({fp.avg_maker_ratio:.0%})")
        if fp.avg_trades_per_minute > 3:
            fp.bot_indicators.append(f"Fast trading ({fp.avg_trades_per_minute:.1f}/min)")
        if fp.avg_position_balance > 0.8:
            fp.bot_indicators.append(f"Balanced positions ({fp.avg_position_balance:.2f})")
        if fp.total_pnl > 50:
            fp.bot_indicators.append(f"Profitable (+${fp.total_pnl:.0f})")
        if fp.avg_edge > 0.02:
            fp.bot_indicators.append(f"Captures {fp.avg_edge:.1%} edge")

        fingerprints.append(fp)

    # Sort by P&L
    fingerprints.sort(key=lambda f: f.total_pnl, reverse=True)

    return fingerprints


# ============================================================================
# TRADE TIMELINE
# ============================================================================

def generate_trade_timeline(
    wallet: str,
    market: MarketMetadata,
    trades: List[ParsedTrade]
) -> str:
    """Generate a detailed trade timeline for a wallet in a market."""

    if not trades:
        return "No trades"

    trades = sorted(trades, key=lambda t: t.timestamp)
    lines = []

    up_total = 0.0
    down_total = 0.0
    up_cost = 0.0
    down_cost = 0.0

    for trade in trades:
        ts = datetime.fromtimestamp(trade.timestamp, tz=timezone.utc)
        time_str = ts.strftime("%H:%M:%S")

        side_str = trade.side.ljust(4)
        outcome_str = trade.outcome.ljust(4)
        role_str = f"({trade.role})"

        if trade.side == "BUY":
            if trade.outcome.lower() == "up":
                up_total += trade.shares
                up_cost += trade.usdc
            else:
                down_total += trade.shares
                down_cost += trade.usdc
        else:
            if trade.outcome.lower() == "up":
                up_total -= trade.shares
            else:
                down_total -= trade.shares

        # Check for complete set
        complete_sets = min(up_total, down_total) if up_total > 0 and down_total > 0 else 0
        edge_marker = ""
        if complete_sets > 0 and up_total > 0 and down_total > 0:
            avg_up = up_cost / up_total if up_total > 0 else 0
            avg_down = down_cost / down_total if down_total > 0 else 0
            if avg_up > 0 and avg_down > 0:
                edge = 1 - (avg_up + avg_down)
                if edge > 0:
                    edge_marker = f" [Edge: {edge:.1%}]"

        line = (f"[{time_str}] {side_str} {outcome_str} "
                f"{trade.shares:>6.1f} @ {trade.price:.3f} {role_str:>8}  "
                f"Up={up_total:>7.1f} Down={down_total:>7.1f}{edge_marker}")
        lines.append(line)

    return "\n".join(lines)


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_wallet_report(
    wallet: str,
    analyses: List[WalletMarketAnalysis],
    fingerprint: WalletStrategyFingerprint,
    wallet_trades: Dict[str, List[ParsedTrade]],
    markets: List[MarketMetadata]
) -> str:
    """Generate detailed report for a single wallet."""

    lines = []
    short = f"{wallet[:6]}...{wallet[-4:]}"

    lines.append("=" * 70)
    lines.append(f"WALLET STRATEGY REPORT: {short}")
    lines.append(f"Full Address: {wallet}")
    lines.append(f"Profile: https://polymarket.com/profile/{wallet}")
    lines.append("=" * 70)

    # Summary
    lines.append("\n## SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Strategy Type:     {fingerprint.strategy_type.upper()}")
    lines.append(f"Total P&L:         ${fingerprint.total_pnl:,.2f}")
    lines.append(f"Total Trades:      {fingerprint.total_trades}")
    lines.append(f"Markets Traded:    {fingerprint.markets_traded}")
    lines.append(f"Avg Edge:          {fingerprint.avg_edge:.2%}")
    lines.append(f"Avg Maker Ratio:   {fingerprint.avg_maker_ratio:.0%}")
    lines.append(f"Position Balance:  {fingerprint.avg_position_balance:.2f}")

    # Bot indicators
    if fingerprint.bot_indicators:
        lines.append("\n## BOT INDICATORS")
        lines.append("-" * 40)
        for indicator in fingerprint.bot_indicators:
            lines.append(f"  - {indicator}")

    # Per-market breakdown
    lines.append("\n## PER-MARKET BREAKDOWN")
    lines.append("-" * 40)

    market_by_slug = {m.slug: m for m in markets}

    for analysis in analyses:
        lines.append(f"\n### {analysis.market_slug}")
        lines.append(f"    Question: {analysis.market_question}")
        lines.append(f"    Winner: {analysis.winning_outcome.upper()}")
        lines.append(f"    Trades: {analysis.total_trades} (Maker: {analysis.maker_ratio:.0%})")
        lines.append(f"    Up: {analysis.up_net:.1f} @ avg ${analysis.avg_up_price:.3f}")
        lines.append(f"    Down: {analysis.down_net:.1f} @ avg ${analysis.avg_down_price:.3f}")
        lines.append(f"    Combined Price: ${analysis.combined_price:.4f}")
        lines.append(f"    Edge: {analysis.edge:.2%}")
        lines.append(f"    Complete Sets: {analysis.complete_sets:.1f}")
        lines.append(f"    P&L: ${analysis.realized_pnl:.2f}")
        lines.append(f"    Trades/min: {analysis.trades_per_minute:.1f}")
        lines.append(f"    Entry Delay: {analysis.entry_delay_secs:.0f}s")
        lines.append(f"    Exit Buffer: {analysis.exit_buffer_secs:.0f}s")

    # Trade timelines
    lines.append("\n## TRADE TIMELINES")
    lines.append("-" * 40)

    for analysis in analyses:
        market = market_by_slug.get(analysis.market_slug)
        trades = wallet_trades.get(analysis.market_slug, [])
        if trades and market:
            lines.append(f"\n### {analysis.market_slug}")
            lines.append(generate_trade_timeline(wallet, market, trades))

    return "\n".join(lines)


def generate_comparison_report(
    fingerprints: List[WalletStrategyFingerprint]
) -> str:
    """Generate comparison report across all wallets."""

    lines = []
    lines.append("=" * 90)
    lines.append("STRATEGY COMPARISON REPORT")
    lines.append("=" * 90)

    # Summary table
    lines.append("\n## RANKING BY P&L")
    lines.append("-" * 90)
    header = (f"{'Rank':<5} {'Wallet':<16} {'Strategy':<12} {'P&L':>10} {'Trades':>8} "
              f"{'Edge':>8} {'Maker%':>8} {'Balance':>8}")
    lines.append(header)
    lines.append("-" * 90)

    for i, fp in enumerate(fingerprints, 1):
        line = (f"{i:<5} {fp.short_wallet:<16} {fp.strategy_type:<12} "
                f"${fp.total_pnl:>8.2f} {fp.total_trades:>8} "
                f"{fp.avg_edge:>7.2%} {fp.avg_maker_ratio:>7.0%} "
                f"{fp.avg_position_balance:>8.2f}")
        lines.append(line)

    # Detailed comparison
    lines.append("\n## TIMING PATTERNS")
    lines.append("-" * 90)
    header = (f"{'Wallet':<16} {'Trades/min':>12} {'Avg Interval':>14} "
              f"{'Entry Delay':>12} {'Exit Buffer':>12}")
    lines.append(header)
    lines.append("-" * 90)

    for fp in fingerprints:
        line = (f"{fp.short_wallet:<16} {fp.avg_trades_per_minute:>12.1f} "
                f"{fp.avg_trade_interval_secs:>12.1f}s "
                f"{fp.avg_entry_delay_secs:>10.0f}s {fp.avg_exit_buffer_secs:>10.0f}s")
        lines.append(line)

    # Strategy insights
    lines.append("\n## KEY INSIGHTS")
    lines.append("-" * 90)

    # Best performer
    best = fingerprints[0]
    lines.append(f"\n1. MOST PROFITABLE: {best.short_wallet}")
    lines.append(f"   - Total P&L: ${best.total_pnl:.2f}")
    lines.append(f"   - Strategy: {best.strategy_type}")
    lines.append(f"   - Key factors: {', '.join(best.bot_indicators[:3])}")

    # Highest edge
    by_edge = sorted(fingerprints, key=lambda f: f.avg_edge, reverse=True)
    highest_edge = by_edge[0]
    lines.append(f"\n2. HIGHEST EDGE: {highest_edge.short_wallet}")
    lines.append(f"   - Avg Edge: {highest_edge.avg_edge:.2%}")
    lines.append(f"   - Position Balance: {highest_edge.avg_position_balance:.2f}")

    # Fastest trader
    by_speed = sorted(fingerprints, key=lambda f: f.avg_trades_per_minute, reverse=True)
    fastest = by_speed[0]
    lines.append(f"\n3. FASTEST TRADER: {fastest.short_wallet}")
    lines.append(f"   - Trades/min: {fastest.avg_trades_per_minute:.1f}")
    lines.append(f"   - Avg Interval: {fastest.avg_trade_interval_secs:.1f}s")

    # Pure arbitrageurs
    arb_wallets = [fp for fp in fingerprints if fp.strategy_type == "arbitrage"]
    lines.append(f"\n4. PURE ARBITRAGEURS: {len(arb_wallets)} wallets")
    for fp in arb_wallets:
        lines.append(f"   - {fp.short_wallet}: balance={fp.avg_position_balance:.2f}, edge={fp.avg_edge:.2%}")

    return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================

def save_results(
    fingerprints: List[WalletStrategyFingerprint],
    wallet_analyses: Dict[str, List[WalletMarketAnalysis]],
    wallet_trades: Dict[str, Dict[str, List[ParsedTrade]]],
    markets: List[MarketMetadata]
):
    """Save all analysis results to files."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)

    # Save fingerprints JSON
    fp_file = OUTPUT_DIR / f"{timestamp}_fingerprints.json"
    fp_data = [asdict(fp) for fp in fingerprints]
    with open(fp_file, "w") as f:
        json.dump(fp_data, f, indent=2)
    print(f"  Fingerprints: {fp_file}")

    # Save per-wallet reports
    for wallet, analyses in wallet_analyses.items():
        if not analyses:
            continue

        fp = next((f for f in fingerprints if f.wallet == wallet), None)
        if not fp:
            continue

        # Get trades for this wallet
        wt = wallet_trades.get(wallet, {})

        report = generate_wallet_report(wallet, analyses, fp, wt, markets)
        short = f"{wallet[:6]}_{wallet[-4:]}"
        report_file = OUTPUT_DIR / f"{timestamp}_{short}_report.txt"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"  Wallet report: {report_file}")

    # Save comparison report
    comparison = generate_comparison_report(fingerprints)
    comp_file = OUTPUT_DIR / f"{timestamp}_comparison.txt"
    with open(comp_file, "w") as f:
        f.write(comparison)
    print(f"  Comparison: {comp_file}")

    # Also print comparison to stdout
    print("\n" + comparison)


def main():
    """Main entry point."""

    print("=" * 70)
    print("TARGET WALLET STRATEGY ANALYZER")
    print(f"Analyzing {len(TARGET_WALLETS)} wallets across {len(MARKETS)} markets")
    print("=" * 70)

    # Phase 1: Fetch data
    markets, all_trades = fetch_all_market_data()

    if not markets:
        print("ERROR: No markets fetched. Exiting.")
        return

    # Phase 2: Filter to target wallets
    wallet_trades = filter_target_wallet_trades(all_trades)

    # Phase 3: Analyze
    wallet_analyses = analyze_all_wallets(markets, wallet_trades)

    # Phase 4: Create fingerprints
    print("\n" + "=" * 70)
    print("PHASE 4: CREATING STRATEGY FINGERPRINTS")
    print("=" * 70)
    fingerprints = create_strategy_fingerprints(wallet_analyses)

    for fp in fingerprints:
        print(f"\n  {fp.short_wallet} ({fp.strategy_type})")
        print(f"    P&L: ${fp.total_pnl:.2f} | Edge: {fp.avg_edge:.2%} | Trades: {fp.total_trades}")

    # Phase 5: Save results
    save_results(fingerprints, wallet_analyses, wallet_trades, markets)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
