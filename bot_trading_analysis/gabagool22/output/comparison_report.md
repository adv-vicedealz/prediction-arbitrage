# gabagool22 Cross-Market Comparison

## Markets Analyzed

| Market | Asset | Time | Winner | P&L |
|--------|-------|------|--------|-----|
| btc-updown-15m-1768037400 | BTC | 4:30-4:45AM | UP | **-$87.14** |
| eth-updown-15m-1768030200 | ETH | 2:30-2:45AM | DOWN | **+$41.45** |

---

## Key Metrics Comparison

| Metric | BTC Market | ETH Market |
|--------|------------|------------|
| **Trades** | 1,377 | 437 |
| **Trades/min** | 93.9 | 31.7 |
| **Duration** | 14.7 min | 13.8 min |
| **Maker Ratio** | 79.6% | 69.6% |
| **Total Volume** | ~$9,900 | ~$1,900 |

---

## Position Analysis

### BTC Market (UP won, they LOST)
| Outcome | Net Position | P&L |
|---------|--------------|-----|
| UP (winner) | 6,410 shares | +$3,006 |
| DOWN (loser) | 6,640 shares | -$3,094 |
| **Net Imbalance** | **-230 (more DOWN)** | |

### ETH Market (DOWN won, they WON)
| Outcome | Net Position | P&L |
|---------|--------------|-----|
| UP (loser) | 1,314 shares | -$697 |
| DOWN (winner) | 1,247 shares | +$738 |
| **Net Imbalance** | **+67 (more UP)** | |

---

## Why They Lost BTC but Won ETH

### BTC Market Loss (-$87)
1. Ended with **230 more DOWN than UP** shares
2. When UP won, those extra DOWN shares became worthless
3. The imbalance cost them: 230 × ~$0.50 avg price = ~$115 loss
4. Not enough edge to offset the directional loss

### ETH Market Win (+$41)
1. Ended with **67 more UP than DOWN** shares
2. When DOWN won, those extra UP shares became worthless
3. But the imbalance was smaller: 67 × ~$0.50 = ~$34 loss
4. **The winning DOWN position offset this loss**

---

## Pattern Analysis

### The Core Issue: Inventory Imbalance

gabagool22's market-making strategy shows a consistent pattern:

1. **They try to stay balanced** - buying both UP and DOWN
2. **But they end up with slight imbalances** - a few hundred shares more of one side
3. **The imbalance determines P&L** - if they hold more of the loser, they lose

| Market | Held More Of | Winner Was | Result |
|--------|--------------|------------|--------|
| BTC | DOWN (+230) | UP | **LOSS** |
| ETH | UP (+67) | DOWN | **WIN** (but had more of loser too!) |

Wait - in ETH they also held more of the loser (UP) but still won? Let's recalculate:

**ETH Reality Check:**
- UP position: 1,314 shares (loser) → worth $0
- DOWN position: 1,247 shares (winner) → worth $1,247
- UP cost: $882, UP revenue: $185 → UP net: -$697
- DOWN cost: $664, DOWN revenue: $154 → DOWN net before payout: -$510
- DOWN payout: $1,247
- DOWN total: $1,247 - $510 = +$737

They won because:
- DOWN shares were bought at lower prices (~$0.41 avg)
- UP shares were bought at higher prices (~$0.53 avg)
- Even though they had more UP shares, the DOWN payout was enough

---

## Strategy Insights

### What Works
1. **Lower average buy price on DOWN** in ETH market (0.41 vs 0.53)
2. **Selling shares** reduces exposure to wrong outcome
3. **Maker orders** at good prices capture edge

### What Doesn't Work
1. **Accumulating too much of one side** without rebalancing
2. **Not exiting fast enough** when market moves directionally
3. **Insufficient edge** (1-2%) to offset inventory risk

---

## Conclusion

gabagool22's strategy is essentially **delta-neutral market making** with imperfect hedging:

- **When inventory stays balanced**: Small consistent profits from spread
- **When inventory gets unbalanced**: P&L depends on which side wins

The -$87 BTC loss and +$41 ETH win are both within the expected variance of this strategy. Over many markets, the wins and losses should roughly cancel out, leaving a small profit from the spread captured.

**Net across both markets: -$87 + $41 = -$46**

This suggests the edge captured (~1.4%) is not sufficient to offset the adverse selection risk in these volatile 15-minute markets.
