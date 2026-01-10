# Trading Strategy Analysis: Wallet 0x6031b6...51f96d

## Executive Summary

After analyzing 2,523 trades across 3 BTC Up/Down markets, this wallet's strategy is clearly identifiable as:

**"Passive Liquidity Accumulation on Both Sides"**

This is NOT arbitrage. It's a market-making strategy that fails due to fee structure.

---

## The Strategy Defined

### Core Mechanism

1. **Place limit BUY orders on BOTH Up and Down** at prices where Up + Down < $1.00
2. **Passively wait** for other traders to fill these orders
3. **Accumulate positions** on both sides throughout the market
4. **Occasionally sell via market orders** (taker) to rebalance
5. **Hold positions through resolution**

### Key Evidence

| Pattern | Data | Interpretation |
|---------|------|----------------|
| 78-80% maker orders | All 3 markets | Passive liquidity provider |
| **100% of maker orders are BUYS** | 0 maker sells | Never providing sell liquidity |
| **100% of sells are taker orders** | Market orders to exit | Reactive, not proactive selling |
| 4-6x more buys than sells | Accumulating, not trading | Not closing positions |
| 45-55% Up/Down balance | Near-perfect split | Attempting market-neutral |
| ~$6 avg trade size | Very consistent | Algorithmic execution |
| 55-87 trades/minute | High frequency | Automated bot |

---

## Why This Strategy Loses Money

### The Math

```
Average cost per Up+Down pair: $0.98-0.99
Theoretical edge: 1-2% per pair
Polymarket fees: 1% maker + 1% taker = ~2% round-trip

Edge (1-2%) < Fees (~2%) = NET LOSS
```

### The Fatal Flaws

1. **Fee Structure Kills the Edge**
   - They buy at ~$0.99 combined (1% edge)
   - But pay ~1% fee on each buy
   - Edge is consumed by entry fees alone

2. **No Position Closing**
   - They accumulate 5,000-6,000 shares per side
   - Never close positions before resolution
   - One side always goes to $0

3. **Not True Arbitrage**
   - True arb: Buy Up+Down simultaneously at < $1, immediately redeem for $1
   - Their strategy: Accumulate passively, hope to profit from spread
   - Problem: No redemption mechanism used

4. **Sells Are Reactive, Not Strategic**
   - All sells are market orders (taker)
   - Paying extra fees to exit
   - Selling at worse prices than they bought

---

## Detailed Breakdown by Market

| Market | Trades | P&L | Fees | Edge | Maker% |
|--------|--------|-----|------|------|--------|
| 5:15AM | 626 | -$395 | $563 | 1.7% | 78% |
| 6:00AM | 1,232 | -$1,355 | $1,185 | 0.5% | 80% |
| 7:00AM | 665 | -$767 | $668 | 1.4% | 78% |
| **TOTAL** | **2,523** | **-$2,518** | **$2,416** | - | - |

**Notice: Total losses ($2,518) ≈ Total fees ($2,416)**

The strategy is essentially break-even BEFORE fees, then fees make it a guaranteed loss.

---

## Order Flow Pattern

```
MAKER ORDERS (78-80%)
├── BUY Up:   100% of Up maker orders
├── BUY Down: 100% of Down maker orders
├── SELL Up:  0%
└── SELL Down: 0%

TAKER ORDERS (20-22%)
├── BUY Up:   ~15% (small)
├── BUY Down: ~10% (small)
├── SELL Up:  ~35% (exits)
└── SELL Down: ~40% (exits)
```

They provide liquidity ONLY on the buy side, then exit via market sells. This is backwards for profitable market making.

---

## What Would Make This Strategy Profitable?

### Option 1: Reduce Fees
- Need fee rebates or lower fee tier
- At 0.5% fees instead of 1%, the edge would be positive

### Option 2: Widen the Spread
- Only buy when Up + Down < $0.96
- Current avg: $0.98-0.99 (too tight)

### Option 3: Close Positions Before Resolution
- Sell both sides before market closes
- Lock in the spread profit
- Avoid binary outcome risk

### Option 4: True Arbitrage
- Buy Up + Down simultaneously
- Immediately merge/redeem for $1
- Requires using Polymarket's CTF (Conditional Token Framework)

### Option 5: Directional Betting
- If going to hold through resolution, pick a side
- Don't waste capital on the losing side

---

## Conclusion

This wallet is running an **automated market-making bot** that:
- ✅ Successfully buys both sides below $1
- ✅ Maintains near-perfect balance
- ✅ Executes at high frequency with consistent size
- ❌ Fails to account for fees in edge calculation
- ❌ Never closes positions profitably
- ❌ Holds through resolution losing one side completely

**Net Result: -$2,518 across 3 markets, almost exactly equal to fees paid.**

The strategy is mathematically sound but economically unprofitable given Polymarket's fee structure.

---

## Data Summary

| Metric | Value |
|--------|-------|
| Total Markets Analyzed | 3 |
| Total Trades | 2,523 |
| Total P&L | -$2,518.12 |
| Total Fees | $2,415.80 |
| Avg Cost Per Pair | $0.9880 |
| Avg Edge | 1.2% |
| Win Rate | 0/3 markets |
