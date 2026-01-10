#!/usr/bin/env python3
"""
Analyze trading strategy for wallet 0x63ce342161250d705dc0b16df89036c8e5f9ba9a
in market btc-updown-15m-1768044600.

This wallet executed a DIRECTIONAL MOMENTUM TRADING strategy, not arbitrage.
"""

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict


TARGET_WALLET = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"
TRADES_FILE = Path(__file__).parent / "trades_1768044600.json"
OUTPUT_FILE = Path(__file__).parent / "wallet_report_0x63ce.json"


@dataclass
class TradingPhase:
    """Represents a distinct phase of trading activity."""
    name: str
    start_time: str
    end_time: str
    description: str
    up_bought: float = 0
    up_sold: float = 0
    down_bought: float = 0
    down_sold: float = 0
    up_cost: float = 0
    up_revenue: float = 0
    down_cost: float = 0
    down_revenue: float = 0
    trade_count: int = 0

    @property
    def up_net(self) -> float:
        return self.up_bought - self.up_sold

    @property
    def down_net(self) -> float:
        return self.down_bought - self.down_sold


@dataclass
class WalletAnalysis:
    """Complete analysis of a wallet's trading activity."""
    wallet: str
    market_slug: str
    market_question: str
    winning_outcome: str

    # Trade counts
    total_trades: int = 0
    maker_trades: int = 0
    taker_trades: int = 0

    # Positions
    up_bought: float = 0
    up_sold: float = 0
    down_bought: float = 0
    down_sold: float = 0
    up_cost: float = 0
    up_revenue: float = 0
    down_cost: float = 0
    down_revenue: float = 0

    # Fees
    total_fees: float = 0

    # Timing
    first_trade_ts: int = 0
    last_trade_ts: int = 0

    # Phases
    phases: List[TradingPhase] = field(default_factory=list)

    # Minting detection
    max_down_short: float = 0  # Maximum negative Down position
    max_up_short: float = 0    # Maximum negative Up position

    @property
    def up_net(self) -> float:
        return self.up_bought - self.up_sold

    @property
    def down_net(self) -> float:
        return self.down_bought - self.down_sold

    @property
    def maker_ratio(self) -> float:
        return self.maker_trades / self.total_trades if self.total_trades > 0 else 0

    @property
    def position_balance(self) -> float:
        """Ratio of smaller to larger position. 1.0 = perfect balance (arbitrage)."""
        up = abs(self.up_net)
        down = abs(self.down_net)
        if up == 0 and down == 0:
            return 0
        if up == 0 or down == 0:
            return 0
        return min(up, down) / max(up, down)

    @property
    def avg_up_buy_price(self) -> float:
        return self.up_cost / self.up_bought if self.up_bought > 0 else 0

    @property
    def avg_down_buy_price(self) -> float:
        return self.down_cost / self.down_bought if self.down_bought > 0 else 0

    @property
    def combined_buy_price(self) -> float:
        """Combined price of buying both outcomes. <$1 = arbitrage opportunity."""
        if self.avg_up_buy_price > 0 and self.avg_down_buy_price > 0:
            return self.avg_up_buy_price + self.avg_down_buy_price
        return 0

    @property
    def strategy_type(self) -> str:
        """Classify the trading strategy."""
        if self.position_balance > 0.80:
            return "ARBITRAGE"
        elif self.position_balance < 0.30:
            return "DIRECTIONAL"
        else:
            return "MIXED"

    @property
    def up_pnl(self) -> float:
        """P&L from Up position."""
        payout = self.up_net * (1.0 if self.winning_outcome == "up" else 0.0)
        return self.up_revenue + payout - self.up_cost

    @property
    def down_pnl(self) -> float:
        """P&L from Down position."""
        payout = self.down_net * (1.0 if self.winning_outcome == "down" else 0.0)
        return self.down_revenue + payout - self.down_cost

    @property
    def total_pnl(self) -> float:
        """Total P&L after fees."""
        return self.up_pnl + self.down_pnl - self.total_fees

    @property
    def trading_duration_mins(self) -> float:
        """Duration from first to last trade in minutes."""
        if self.last_trade_ts > self.first_trade_ts:
            return (self.last_trade_ts - self.first_trade_ts) / 60
        return 0

    @property
    def trades_per_minute(self) -> float:
        """Average trades per minute."""
        if self.trading_duration_mins > 0:
            return self.total_trades / self.trading_duration_mins
        return 0


def load_trades(wallet: str) -> tuple:
    """Load and filter trades for target wallet."""
    with open(TRADES_FILE) as f:
        data = json.load(f)

    market = data["market"]
    all_trades = data["trades"]

    wallet_trades = [t for t in all_trades if t["wallet"] == wallet]
    wallet_trades.sort(key=lambda t: (t["timestamp"], t["id"]))

    return market, wallet_trades


def detect_phases(trades: List[dict]) -> List[TradingPhase]:
    """Detect distinct trading phases based on activity patterns."""
    phases = []

    # Phase boundaries (timestamps in seconds)
    # Phase 1: 11:30-11:35 (initial Up accumulation)
    # Phase 2: 11:36 (reversal)
    # Phase 3: 11:37-11:44 (volatile accumulation)

    phase_bounds = [
        (1768044626, 1768044960, "Phase 1: Initial Up Bet",
         "Bought Up aggressively, shorted Down via minting"),
        (1768044960, 1768045020, "Phase 2: Reversal",
         "Sold Up shares, bought Down heavily"),
        (1768045020, 1768045500, "Phase 3: Volatile Accumulation",
         "Continued accumulating Down through market volatility")
    ]

    for start_ts, end_ts, name, desc in phase_bounds:
        phase_trades = [t for t in trades if start_ts <= t["timestamp"] < end_ts]

        if not phase_trades:
            continue

        phase = TradingPhase(
            name=name,
            start_time=datetime.utcfromtimestamp(start_ts).strftime("%H:%M:%S"),
            end_time=datetime.utcfromtimestamp(end_ts).strftime("%H:%M:%S"),
            description=desc,
            trade_count=len(phase_trades)
        )

        for t in phase_trades:
            if t["outcome"] == "Up":
                if t["side"] == "BUY":
                    phase.up_bought += t["shares"]
                    phase.up_cost += t["usdc"]
                else:
                    phase.up_sold += t["shares"]
                    phase.up_revenue += t["usdc"]
            else:  # Down
                if t["side"] == "BUY":
                    phase.down_bought += t["shares"]
                    phase.down_cost += t["usdc"]
                else:
                    phase.down_sold += t["shares"]
                    phase.down_revenue += t["usdc"]

        phases.append(phase)

    return phases


def track_position_over_time(trades: List[dict]) -> tuple:
    """Track position and detect minting (negative positions)."""
    up_pos = 0
    down_pos = 0
    max_down_short = 0
    max_up_short = 0

    position_history = []

    for t in trades:
        if t["outcome"] == "Up":
            if t["side"] == "BUY":
                up_pos += t["shares"]
            else:
                up_pos -= t["shares"]
        else:  # Down
            if t["side"] == "BUY":
                down_pos += t["shares"]
            else:
                down_pos -= t["shares"]

        # Track maximum short positions (negative = minting required)
        if down_pos < 0:
            max_down_short = min(max_down_short, down_pos)
        if up_pos < 0:
            max_up_short = min(max_up_short, up_pos)

        position_history.append({
            "timestamp": t["timestamp"],
            "up_pos": round(up_pos, 2),
            "down_pos": round(down_pos, 2)
        })

    return position_history, abs(max_down_short), abs(max_up_short)


def analyze_wallet(wallet: str) -> WalletAnalysis:
    """Perform complete analysis of wallet trading activity."""
    market, trades = load_trades(wallet)

    analysis = WalletAnalysis(
        wallet=wallet,
        market_slug=market["slug"],
        market_question=market["question"],
        winning_outcome=market["winning_outcome"]
    )

    # Basic counts
    analysis.total_trades = len(trades)
    analysis.maker_trades = len([t for t in trades if t["role"] == "maker"])
    analysis.taker_trades = len([t for t in trades if t["role"] == "taker"])

    # Aggregate positions
    for t in trades:
        if t["outcome"] == "Up":
            if t["side"] == "BUY":
                analysis.up_bought += t["shares"]
                analysis.up_cost += t["usdc"]
            else:
                analysis.up_sold += t["shares"]
                analysis.up_revenue += t["usdc"]
        else:  # Down
            if t["side"] == "BUY":
                analysis.down_bought += t["shares"]
                analysis.down_cost += t["usdc"]
            else:
                analysis.down_sold += t["shares"]
                analysis.down_revenue += t["usdc"]

        # Fees (only on maker trades)
        if t["role"] == "maker":
            analysis.total_fees += t["fee"]

    # Timing
    timestamps = [t["timestamp"] for t in trades]
    analysis.first_trade_ts = min(timestamps)
    analysis.last_trade_ts = max(timestamps)

    # Phases
    analysis.phases = detect_phases(trades)

    # Minting detection
    _, max_down_short, max_up_short = track_position_over_time(trades)
    analysis.max_down_short = max_down_short
    analysis.max_up_short = max_up_short

    return analysis


def generate_report(analysis: WalletAnalysis) -> dict:
    """Generate comprehensive JSON report."""
    report = {
        "wallet": analysis.wallet,
        "market": {
            "slug": analysis.market_slug,
            "question": analysis.market_question,
            "winning_outcome": analysis.winning_outcome
        },
        "summary": {
            "strategy_type": analysis.strategy_type,
            "total_trades": analysis.total_trades,
            "maker_trades": analysis.maker_trades,
            "taker_trades": analysis.taker_trades,
            "maker_ratio": round(analysis.maker_ratio, 4),
            "position_balance": round(analysis.position_balance, 4),
            "combined_buy_price": round(analysis.combined_buy_price, 4),
            "trading_duration_mins": round(analysis.trading_duration_mins, 2),
            "trades_per_minute": round(analysis.trades_per_minute, 2),
            "first_trade": datetime.utcfromtimestamp(analysis.first_trade_ts).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "last_trade": datetime.utcfromtimestamp(analysis.last_trade_ts).strftime("%Y-%m-%d %H:%M:%S UTC")
        },
        "positions": {
            "up": {
                "bought": round(analysis.up_bought, 2),
                "sold": round(analysis.up_sold, 2),
                "net": round(analysis.up_net, 2),
                "cost": round(analysis.up_cost, 2),
                "revenue": round(analysis.up_revenue, 2),
                "avg_buy_price": round(analysis.avg_up_buy_price, 4)
            },
            "down": {
                "bought": round(analysis.down_bought, 2),
                "sold": round(analysis.down_sold, 2),
                "net": round(analysis.down_net, 2),
                "cost": round(analysis.down_cost, 2),
                "revenue": round(analysis.down_revenue, 2),
                "avg_buy_price": round(analysis.avg_down_buy_price, 4)
            }
        },
        "pnl": {
            "up_pnl": round(analysis.up_pnl, 2),
            "down_pnl": round(analysis.down_pnl, 2),
            "total_fees": round(analysis.total_fees, 2),
            "total_pnl": round(analysis.total_pnl, 2)
        },
        "minting": {
            "max_down_short": round(analysis.max_down_short, 2),
            "max_up_short": round(analysis.max_up_short, 2),
            "minting_detected": analysis.max_down_short > 0 or analysis.max_up_short > 0,
            "explanation": "Negative position indicates shares were sold before being bought, requiring minting (paying $1 to create Up+Down pair)"
        },
        "phases": [
            {
                "name": p.name,
                "start_time": p.start_time,
                "end_time": p.end_time,
                "description": p.description,
                "trade_count": p.trade_count,
                "up_net": round(p.up_net, 2),
                "down_net": round(p.down_net, 2)
            }
            for p in analysis.phases
        ],
        "key_insights": [
            f"Strategy: {analysis.strategy_type} (position balance = {analysis.position_balance:.2f})",
            f"Combined buy price: ${analysis.combined_buy_price:.4f} (>$1 = not arbitrage)",
            f"Final P&L: ${analysis.total_pnl:.2f}",
            f"Ended on WINNING side (Down) but still lost money",
            f"High fees (${analysis.total_fees:.2f}) destroyed potential profit",
            f"Minting detected: shorted {analysis.max_down_short:.0f} Down shares before buying"
        ],
        "analysis_timestamp": datetime.utcnow().isoformat() + "Z"
    }

    return report


def main():
    print("=" * 60)
    print("WALLET STRATEGY ANALYSIS")
    print("=" * 60)
    print(f"Wallet: {TARGET_WALLET}")
    print()

    # Analyze
    analysis = analyze_wallet(TARGET_WALLET)

    # Print summary
    print(f"Market: {analysis.market_question}")
    print(f"Winner: {analysis.winning_outcome.upper()}")
    print()
    print(f"Strategy Type: {analysis.strategy_type}")
    print(f"Total Trades: {analysis.total_trades}")
    print(f"Maker Ratio: {analysis.maker_ratio:.1%}")
    print(f"Position Balance: {analysis.position_balance:.4f}")
    print(f"Combined Buy Price: ${analysis.combined_buy_price:.4f}")
    print()
    print("POSITIONS:")
    print(f"  Up: {analysis.up_net:+.2f} shares (bought {analysis.up_bought:.0f}, sold {analysis.up_sold:.0f})")
    print(f"  Down: {analysis.down_net:+.2f} shares (bought {analysis.down_bought:.0f}, sold {analysis.down_sold:.0f})")
    print()
    print("P&L:")
    print(f"  Up P&L: ${analysis.up_pnl:.2f}")
    print(f"  Down P&L: ${analysis.down_pnl:.2f}")
    print(f"  Fees: ${analysis.total_fees:.2f}")
    print(f"  TOTAL: ${analysis.total_pnl:.2f}")
    print()

    if analysis.max_down_short > 0:
        print(f"MINTING DETECTED: Max Down short = {analysis.max_down_short:.0f} shares")

    # Generate and save report
    report = generate_report(analysis)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    print()
    print(f"Report saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
