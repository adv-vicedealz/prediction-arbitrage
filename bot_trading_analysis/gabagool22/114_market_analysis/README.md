# gabagool22 - 114 Market Analysis

**Wallet**: `0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d`
**Analysis Date**: January 11, 2026

## Summary

| Metric | Value |
|--------|-------|
| Markets Analyzed | 114 |
| Total Trades | 68,794 |
| Total P&L | **+$3,211.29** |
| Win Rate | 72.8% |
| Effective Edge | 0.94% |

## Files in This Folder

| File | Description |
|------|-------------|
| `COMPREHENSIVE_ANALYSIS_114.md` | Full statistical analysis report |
| `comprehensive_analysis_114.png` | 4-panel overview chart (P&L trend, distribution, maker ratio, BTC vs ETH) |
| `strategy_deep_dive_*.png` | Individual market deep-dives showing trade-by-trade analysis |
| `all_market_results.json` | Raw data for all 114 markets |

## Charts Overview

### comprehensive_analysis_114.png
- **Top-Left**: Cumulative P&L across 114 markets
- **Top-Right**: P&L distribution histogram (green=wins, red=losses)
- **Bottom-Left**: Maker ratio vs P&L scatter plot
- **Bottom-Right**: Performance by asset (BTC vs ETH)

### strategy_deep_dive_*.png
For each individual market:
- Price evolution with trade markers
- Position evolution (UP vs DOWN shares)
- Net position over time
- Cumulative P&L
- Trade distribution by price level
- Maker vs Taker breakdown

## Strategy Classification

gabagool22 operates as a **Delta-Neutral Market Maker**:
- Posts limit orders on both UP and DOWN outcomes
- Captures the bid-ask spread (~1% edge)
- 80% maker ratio (limit orders)
- Maintains roughly balanced positions
- Profits from spread regardless of winner

## Key Insights

1. **Statistically Significant**: p-value = 0.0002 (not luck)
2. **Consistent**: 73% win rate across 114 markets
3. **Risk-Managed**: Max loss $284, avg loss $50
4. **Scalable**: Works on both BTC and ETH markets
