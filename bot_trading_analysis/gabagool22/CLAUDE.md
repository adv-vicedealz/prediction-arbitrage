# gabagool22 Trading Strategy Analysis

## Project Overview
Analysis of wallet `0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d` (gabagool22) trading on Polymarket updown markets.

## Key Findings
- **Strategy**: Delta-neutral market maker
- **Total P&L**: $3,211.29 across 114 markets
- **Win Rate**: 72.8%
- **Edge**: 0.94% on volume
- **Maker Ratio**: 80%

## How The Strategy Works
1. Posts BUY limit orders on BOTH UP and DOWN outcomes
2. Being a MAKER (not TAKER) saves ~$0.11 per pair
3. Combined cost: ~$0.96 for guaranteed $1.00 payout
4. Tries to stay delta-neutral (equal UP and DOWN positions)
5. Risk: One-sided fills cause imbalanced positions

## Key Files
- `114_market_analysis/GABAGOOL22_STRATEGY_GUIDE.md` - Comprehensive strategy documentation
- `114_market_analysis/all_market_results.json` - Raw data for 114 markets
- `data/btc-updown-15m-*.json` - Individual market trade data

## Visualizations Created
- `comprehensive_analysis_114.png` - 4-panel overview
- `timing_mechanics.png` - Position building over time
- `cost_basis_analysis.png` - Spread capture analysis
- `pricing_algorithm.png` - Order placement strategy
- `one_sided_fills.png` - Risk visualization
- `strategy_deep_dive_*.png` - Individual market examples

## Scripts
- `fetch_100_markets.py` - Fetch recent markets for analysis
- `generate_comprehensive_report.py` - Generate statistics and charts
- `deep_strategy_analysis.py` - Individual market deep dives
- `timing_analysis.py` - Trade timing patterns
- `pricing_algorithm.py` - Order pricing visualization

## Data Sources
- Polymarket Goldsky Subgraph (orderFilledEvents)
- Gamma API for market metadata
- Market slug format: `{asset}-updown-15m-{timestamp}`

## Analysis Date
January 11, 2026
