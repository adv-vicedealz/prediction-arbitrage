# gabagool22 Comprehensive Trading Analysis

**Wallet**: `0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d`
**Analysis Date**: January 11, 2026
**Data Source**: Polymarket Goldsky Subgraph

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Markets Analyzed** | 114 |
| **Total Trades** | 68,794 |
| **Win Rate** | 72.8% (83/31) |
| **Total P&L** | **$3,211.29** |
| **Avg P&L/Market** | $28.17 |
| **Effective Edge** | 0.94% |
| **Profit Factor** | 3.05x |

**Verdict**: gabagool22 is a **statistically profitable delta-neutral market maker** with a verified edge.

---

## 1. P&L Statistics

| Metric | Value |
|--------|-------|
| Total P&L | $3,211.29 |
| Mean P&L | $28.17 |
| Median P&L | $27.05 |
| Std Deviation | $78.72 |
| Min (worst loss) | $-284.00 |
| Max (best win) | $393.75 |

### Statistical Confidence
- **95% Confidence Interval**: [$13.72, $42.62] per market
- **P-value**: 0.0002 (highly significant)
- **Conclusion**: Profitability is NOT due to luck

---

## 2. Win/Loss Analysis

| Metric | Value |
|--------|-------|
| Wins | 83 markets |
| Losses | 31 markets |
| Win Rate | 72.8% |
| Avg Win | $57.52 |
| Avg Loss | $-50.41 |
| Win/Loss Ratio | 1.14x |
| Profit Factor | 3.05x |

### Interpretation
- The high win rate (73%) is the main driver of profitability
- Profit factor of 3.05x means they earn $3.05 for every $1 they lose

---

## 3. Performance by Asset

| Asset | Markets | Total P&L | Win Rate | Avg P&L |
|-------|---------|-----------|----------|---------|
| BTC | 66 | $1,964.67 | 66.7% | $29.77 |
| ETH | 48 | $1,246.63 | 81.2% | $25.97 |

### Observations
- BTC generates most of the profit
- Strategy works on both assets

---

## 4. Performance by Market Outcome

| When Winner Is | Markets | Total P&L | Avg P&L |
|----------------|---------|-----------|---------|
| UP | 53 | $1022.75 | $19.30 |
| DOWN | 61 | $2188.54 | $35.88 |

---

## 5. Position Bias Analysis

| Bias Status | Markets | Total P&L | Avg P&L |
|-------------|---------|-----------|---------|
| Correct (bias matches winner) | 68 (60%) | $4224.53 | $62.13 |
| Wrong (bias doesn't match) | 46 (40%) | $-1013.24 | $-22.03 |

### Interpretation
- They predict the winner correctly only 60% of the time
- When correct, they profit more; when wrong, they lose less
- **This asymmetry is the source of their edge**

---

## 6. Maker Ratio Impact

| Maker Ratio | Markets | Total P&L | Avg P&L |
|-------------|---------|-----------|---------|
| High (>=80%) | 54 | $2170.62 | $40.20 |
| Low (<80%) | 60 | $1040.68 | $17.34 |

**Average Maker Ratio**: 80.0%

### Interpretation
- Higher maker ratio = more profit
- Being the maker (posting limit orders) captures the spread

---

## 7. Edge Calculation

| Metric | Value |
|--------|-------|
| Total Volume Traded | $341,511.42 |
| Total P&L | $3,211.29 |
| **Effective Edge** | **0.94%** |

### Interpretation
For every $100 traded, they profit $0.94 on average.

---

## 8. Top & Bottom Markets

### Best 10 Markets
| Market | P&L | Trades | Winner |
|--------|-----|--------|--------|
| btc-updown-15m-1767311100 | $393.75 | 1781 | DOWN |
| btc-updown-15m-1765759500 | $325.74 | 916 | UP |
| btc-updown-15m-1767155400 | $191.85 | 960 | DOWN |
| btc-updown-15m-1767415500 | $191.09 | 876 | UP |
| btc-updown-15m-1766457000 | $167.26 | 658 | DOWN |
| btc-updown-15m-1767620700 | $151.25 | 1014 | UP |
| btc-updown-15m-1765805400 | $115.99 | 1155 | UP |
| eth-updown-15m-1766374200 | $115.78 | 437 | DOWN |
| btc-updown-15m-1768069800 | $113.31 | 584 | UP |
| btc-updown-15m-1762821000 | $112.24 | 518 | DOWN |

### Worst 10 Markets
| Market | P&L | Trades | Winner |
|--------|-----|--------|--------|
| btc-updown-15m-1768074300 | $-47.53 | 1142 | DOWN |
| btc-updown-15m-1768079700 | $-49.46 | 773 | UP |
| eth-updown-15m-1767499200 | $-52.72 | 577 | UP |
| btc-updown-15m-1768059900 | $-74.97 | 764 | UP |
| btc-updown-15m-1768071600 | $-97.05 | 497 | DOWN |
| btc-updown-15m-1768070700 | $-105.25 | 1071 | DOWN |
| btc-updown-15m-1768044600 | $-123.22 | 817 | DOWN |
| btc-updown-15m-1766151000 | $-155.98 | 906 | UP |
| btc-updown-15m-1767722400 | $-159.20 | 1091 | UP |
| btc-updown-15m-1767576600 | $-284.00 | 1103 | UP |

---

## 9. Strategy Classification

gabagool22 operates as a **High-Frequency Delta-Neutral Market Maker**:

### Core Strategy
1. **Post limit orders on both UP and DOWN** (80.0% maker ratio)
2. **Maintain balanced positions** (try to hold equal amounts)
3. **Capture the spread** (buy both sides for combined < $1.00)
4. **Profit from resolution** (net positions pay out at $1.00)

### Why It Works
1. **Spread capture**: 0.94% edge on all volume
2. **Asymmetric payoffs**: Win more when correct, lose less when wrong
3. **High win rate**: 72.8% of markets are profitable
4. **Contained risk**: Max loss is $284, avg loss is $50

### Weaknesses
1. **Inventory risk**: Can get stuck with imbalanced positions
2. **Adverse selection**: Informed traders can pick them off
3. **Volatility**: Extreme price moves hurt performance

---

## Visualizations

![Comprehensive Analysis](comprehensive_analysis_114.png)

---

## Conclusion

gabagool22 is a **verified profitable market maker** on Polymarket:

| Finding | Evidence |
|---------|----------|
| **Profitable** | +$3,211 across 114 markets |
| **Consistent** | 73% win rate, 3.05x profit factor |
| **Statistical edge** | 0.94% edge, p-value 0.0002 |
| **Risk-managed** | Max drawdown $284 |
| **Scalable** | Works on both BTC and ETH |

### Expected Future Performance
Based on this data:
- **Expected P&L per market**: $28.17 (95% CI: $13.72-$42.62)
- **Expected win rate**: ~73%
- **Expected edge**: ~0.9%

---

*Generated on January 11, 2026 at 00:22:42*
