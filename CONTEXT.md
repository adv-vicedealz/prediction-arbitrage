# Prediction Arbitrage Project Context

## Overview

This project analyzes and replicates a **market making strategy** on Polymarket's BTC Up/Down 15-minute binary markets. The strategy profits by buying both outcomes (Up and Down) at combined prices below $1.00, guaranteeing profit regardless of which outcome wins.

## Discovery: The Reference Wallet

We analyzed wallet `0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d` which executes this strategy profitably. Key findings:

- **Strategy**: Buy Up at $0.48 + Buy Down at $0.49 = $0.97 total → $0.03 guaranteed profit per share pair
- **Volume**: Trades every 15-minute BTC market
- **Edge**: Captures 2-5% edge per complete set
- **Risk**: Inventory imbalance when fills happen at different times

## Paper Trading System

We built a paper trading system to test and learn from the strategy without real money.

### Why Paper Trading (Not Backtesting)

Historic trade data only shows filled orders, not the live orderbook. We can't simulate realistic bid/ask spreads from historic data alone. Paper trading with live orderbook data is more accurate.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTINUOUS TRADER                         │
│  - Auto-discovers BTC Up/Down markets via Gamma API         │
│  - Polls live orderbooks from CLOB API                      │
│  - Simulates fills with random probability (realistic)      │
│  - Tracks inventory, rebalancing, P&L                       │
│  - Saves session results to JSON                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       ANALYZER                               │
│  - Loads all session results                                │
│  - Calculates win/loss, edge, imbalance metrics             │
│  - Identifies patterns in profitable vs losing sessions     │
│  - Generates parameter adjustment recommendations           │
└─────────────────────────────────────────────────────────────┘
```

### Files Created

| File | Purpose |
|------|---------|
| `paper_trading/paper_trader.py` | Single-session paper trading bot with live orderbook |
| `paper_trading/continuous_trader.py` | Auto-discovers markets, trades continuously, records results |
| `paper_trading/analyzer.py` | Analyzes performance, identifies patterns, suggests improvements |
| `paper_trading/market_scanner.py` | Finds active BTC Up/Down markets |
| `paper_trading/find_active_market.py` | Market discovery utilities |
| `paper_trading/selected_market.json` | Current market configuration |
| `paper_trading/session_results.json` | Raw results from paper trading session |
| `paper_trading/data/` | Directory for storing session results |

### Key Configuration (continuous_trader.py)

```python
CONFIG = {
    "target_edge": 0.03,          # Target 3% edge (combined < $0.97)
    "size_per_fill": 25,          # Shares per simulated fill
    "fill_probability": 0.40,     # 40% chance of fill per poll
    "max_inventory_ratio": 1.5,   # Rebalance if ratio > 1.5
    "rebalance_size": 25,         # Shares to rebalance
    "poll_interval": 3,           # Seconds between polls
}
```

## Critical Bug Fix: Orderbook Parsing

**Problem**: Initially got 98% spreads when actual market had 1-2% spreads.

**Root Cause**: Polymarket CLOB API returns bids sorted ASCENDING (lowest first), not descending.

**Fix**:
```python
@property
def best_bid(self) -> Optional[float]:
    # Bids sorted ascending - best bid is MAX (highest price buyer)
    return max(float(b["price"]) for b in self.bids)

@property
def best_ask(self) -> Optional[float]:
    # Asks sorted descending - best ask is MIN (lowest price seller)
    return min(float(a["price"]) for a in self.asks)
```

## APIs Used

| API | Endpoint | Purpose |
|-----|----------|---------|
| Gamma API | `https://gamma-api.polymarket.com` | Market discovery, metadata |
| CLOB API | `https://clob.polymarket.com` | Live orderbooks, token details |
| Goldsky Subgraph | GraphQL | Historic trade data for analysis |

## First Paper Trading Session Results

**Market**: Bitcoin Up or Down - January 9, 6:45PM-7:00PM ET

| Metric | Value |
|--------|-------|
| P&L | $59.13 |
| Edge | 4.4% |
| Fills | 110 |
| Complete Sets | 1,350 |
| Unhedged Up | 50 |
| Inventory Imbalance | 1.04x |
| Winner | Down |
| Duration | 7.9 minutes |

## Learning System Plan

The analyzer tracks across multiple sessions:

1. **Win/Loss Correlation**
   - Imbalance vs P&L
   - Position bias in winners vs losers

2. **Parameter Optimization**
   - Suggests lowering `max_inventory_ratio` if high imbalance causes losses
   - Suggests increasing `target_edge` if average edge is too low
   - Suggests adjusting `fill_probability` based on actual fill rates

3. **Pattern Detection**
   - Which market conditions are most profitable
   - When rebalancing helps vs hurts

## Next Steps

1. **Run continuous trader** on multiple markets to gather data:
   ```bash
   python3 paper_trading/continuous_trader.py
   ```

2. **Analyze results** after 10+ sessions:
   ```bash
   python3 paper_trading/analyzer.py
   ```

3. **Tune parameters** based on analyzer recommendations

4. **Future improvements**:
   - Add real fill detection (compare paper fills to actual market trades)
   - Implement more sophisticated rebalancing logic
   - Add market condition filters (volatility, volume)
   - Consider live trading after sufficient paper testing

## Data Directory Structure

```
paper_trading/
├── data/
│   └── session_*.json          # Individual session results
├── all_results.json            # Aggregated results
├── analysis_report.json        # Latest analysis output
├── session_results.json        # Most recent session raw data
└── selected_market.json        # Current market config
```

## Quick Reference Commands

```bash
# Find next market
python3 paper_trading/market_scanner.py

# Run single session paper trader
python3 paper_trading/paper_trader.py

# Run continuous trader (auto-discovers markets)
python3 paper_trading/continuous_trader.py

# Analyze all sessions
python3 paper_trading/analyzer.py
```
