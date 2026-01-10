# Market Making Strategy on Polymarket Binary Markets

## Overview

This document explains the market making strategy used by wallet `0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d` on the BTC Up/Down market (January 9, 2026, 3:00PM-3:15PM ET).

---

## 1. The Core Concept: Binary Markets

In a binary market (e.g., "Will BTC go Up or Down?"), there are two outcomes:

| Outcome | If Up Wins | If Down Wins |
|---------|------------|--------------|
| Up share | $1.00 | $0.00 |
| Down share | $0.00 | $1.00 |

**Key insight:** If you hold 1 Up + 1 Down = "Complete Set" = **Always worth $1.00**

```
Complete Set Value:
  If Up wins:   1×$1.00 + 1×$0.00 = $1.00
  If Down wins: 1×$0.00 + 1×$1.00 = $1.00

  → No matter who wins, you get $1.00!
```

---

## 2. The Arbitrage Opportunity

If you can buy 1 Up + 1 Down for **less than $1.00 combined**, you have guaranteed profit.

### Example:
```
Buy 100 Up   @ $0.45 = $45.00
Buy 100 Down @ $0.52 = $52.00
────────────────────────────
Total cost:            $97.00

At resolution: 100 complete sets × $1.00 = $100.00
PROFIT: $3.00 (guaranteed, no matter which side wins!)
```

---

## 3. The Market Making Strategy

### Step 1: Post Bids on BOTH Order Books

The trader posts limit buy orders (bids) on both sides simultaneously:

```
    UP ORDER BOOK                       DOWN ORDER BOOK
    ==================                  ==================

    ASKS (sellers)                      ASKS (sellers)
    $0.55 ████ 200 shares               $0.58 ████ 200 shares
    $0.54 ███ 150 shares                $0.57 ███ 150 shares
    ──────────────────                  ──────────────────
    $0.52 ████ [THEIR BID]              $0.46 ████ [THEIR BID]  ← Combined = $0.98
    $0.51 ███ [THEIR BID]               $0.45 ███ [THEIR BID]  ← Combined = $0.96
    $0.50 ██ other bids                 $0.44 ██ other bids

    BIDS (buyers)                       BIDS (buyers)
```

**The key:** Their bid prices are set so that `Up_bid + Down_bid < $1.00`

### Step 2: Wait for Fills

When someone wants to SELL shares, they hit the trader's bids:

```
Seller A has Up shares, wants USDC → Sells to trader's Up bid
Seller B has Down shares, wants USDC → Sells to trader's Down bid
```

The trader accumulates inventory on both sides.

### Step 3: Hold to Resolution

At market resolution:
- One side pays $1.00, the other pays $0.00
- Each complete set (1 Up + 1 Down) returns $1.00
- Profit = $1.00 - average combined purchase price

---

## 4. Important: Timing Does NOT Matter

**Common misconception:** "They must buy Up and Down at the same time"

**Reality:** They buy at DIFFERENT times. Only the final weighted average matters.

### Example from actual trades:

| # | Time | Buy | Shares | Price | Up Total | Down Total | Complete Sets |
|---|------|-----|--------|-------|----------|------------|---------------|
| 1 | 20:00:16 | Up | 8.9 | $0.43 | 8.9 | 0 | 0 |
| 2 | 20:00:18 | Up | 11.0 | $0.43 | 19.9 | 0 | 0 |
| ... | ... | Up | ... | ... | 115.7 | 0 | 0 |
| 9 | 20:00:20 | Down | 24.0 | $0.56 | 115.7 | 24.0 | **24** |
| 10 | 20:00:20 | Up | 14.1 | $0.44 | 129.8 | 24.0 | 24 |
| 12 | 20:00:22 | Down | 24.0 | $0.56 | 139.7 | 48.0 | **48** |

**Pattern:** Each time they buy the minority side, more complete sets form!

### Final weighted average:

```
After 647 maker buys across 14 minutes:
  Up:   4,492 shares @ avg $0.5638
  Down: 4,481 shares @ avg $0.4166
  ─────────────────────────────────
  Combined average: $0.9804

Profit per complete set: $1.00 - $0.9804 = $0.0196
Complete sets: 4,481
Guaranteed profit: ~$88
```

---

## 5. THE RISK: Unbalanced Inventory

### The Problem

Bids get filled at **random times** depending on when sellers arrive. If the market moves, one side may fill much more than the other.

### Example Scenario:

```
Step 1: Trader posts bids
  Buy Up @ $0.30
  Buy Down @ $0.68
  Combined = $0.98 < $1.00 ✓

Step 2: Partial fill
  After 30 seconds: Up bid fills @ $0.30 ✓
  Trader now owns: 100 Up shares

Step 3: Market moves!
  Down price jumps to $0.80
  Their $0.68 Down bid is too low - nobody will sell there
  Down bid NEVER fills ✗

Step 4: Result
  Trader owns: 100 Up, 0 Down
  This is NOT a complete set - it's a DIRECTIONAL BET!

  If Up wins:   100 × $1.00 = $100 → PROFIT
  If Down wins: 100 × $0.00 = $0   → LOSS of $30
```

### This Happened to This Trader!

The market moved dramatically during the 14-minute trading window:

| Time | Up Price | Down Price | What Happened |
|------|----------|------------|---------------|
| 20:00 | $0.38 | $0.64 | Down expensive, hard to buy |
| 20:03 | $0.55 | $0.44 | Balanced |
| 20:07 | $0.66 | $0.34 | Down getting cheaper |
| 20:10 | $0.92 | $0.08 | Down very cheap, Up expensive |
| 20:14 | $0.98 | $0.03 | Down almost worthless |

**Result:** They ended up with unbalanced inventory:

```
Final holdings:
  Up shares:   3,509
  Down shares: 3,974
  ─────────────────────
  Difference:  465 MORE Down than Up

Breakdown:
  Complete sets: 3,509 (hedged, safe)
  Extra Down:    465 (unhedged, risky!)
```

### P&L Impact:

```
Complete sets (3,509):
  Cost: ~$3,439
  Payout: $3,509
  Profit: ~$70 (guaranteed)

Extra Down shares (465):
  Cost: ~$194
  If Down wins: +$271 profit
  If Up wins:   -$194 loss  ← This is what likely happened!

Net result (if Up won):
  $70 - $194 = -$124 LOSS
```

---

## 6. Key Metrics from This Trader

| Metric | Value |
|--------|-------|
| Trading window | 14 minutes |
| Total trades | 816 |
| Trades per minute | 57 |
| Maker trades (bids filled) | 647 (79%) |
| Taker trades (rebalancing) | 169 (21%) |

### Maker Buys (Core Strategy):
| Side | Shares | Avg Price | Cost |
|------|--------|-----------|------|
| Up | 4,492 | $0.5638 | $2,533 |
| Down | 4,481 | $0.4166 | $1,867 |
| **Combined** | - | **$0.9804** | $4,400 |

### Final Position:
| Side | Net Shares |
|------|------------|
| Up | 3,509 |
| Down | 3,974 |
| Unhedged Down | 465 |

---

## 7. Summary

### The Strategy:
1. Post bids on BOTH sides with combined price < $1.00
2. Accumulate inventory as sellers hit your bids
3. Hold complete sets to resolution for guaranteed profit

### The Risk:
1. Market moves can cause unbalanced fills
2. Unmatched shares become directional bets
3. Can lose money if wrong side wins

### Key Insight:
```
Timing of individual trades does NOT matter.
Only the FINAL weighted average price matters.
But staying BALANCED is critical to avoid directional risk.
```

---

## 8. Risk Management Techniques

To manage unbalanced inventory, the trader uses three techniques:

### Technique 1: Dynamic Bid Adjustment

As the market moves, they adjust bid prices on both sides to:
- Stay competitive (get fills)
- Keep combined bid price < $1.00

#### The Concept: Layered Bids

The trader doesn't post just ONE bid. They post a **LADDER** of bids at multiple price levels:

```
    UP ORDER BOOK                       DOWN ORDER BOOK
    (at start of market)                (at start of market)

    $0.44 ████ [their bid]              $0.67 ████ [their bid]
    $0.43 ████ [their bid]              $0.64 ████ [their bid]
    $0.40 ████ [their bid]              $0.61 ████ [their bid]
    $0.37 ████ [their bid]              $0.58 ████ [their bid]
    $0.35 ████ [their bid]              $0.56 ████ [their bid]
    $0.30 ████ [their bid]
```

#### Why Layered Bids?

1. **Catch large sells** - When someone dumps, it eats through multiple levels
2. **Better average price** - Lower bids get better prices on big moves
3. **Always in market** - Even if top bids fill, lower ones remain active
4. **Protection** - Can't update orders fast enough in volatile markets

#### How the Ladder Shifts

| Time | Up Bid Ladder | Down Bid Ladder | Market |
|------|---------------|-----------------|--------|
| +0:00 | $0.30-$0.44 | $0.56-$0.68 | Up ~38% |
| +3:00 | $0.42-$0.61 | $0.37-$0.53 | Up ~55% |
| +7:00 | $0.58-$0.74 | $0.25-$0.41 | Up ~68% |
| +11:00 | $0.69-$0.93 | $0.05-$0.29 | Up ~85% |

The ENTIRE ladder shifts:
- Up bids rose from $0.30-0.44 → $0.69-0.93 (+$0.40 shift!)
- Down bids fell from $0.56-0.68 → $0.05-0.29 (-$0.40 shift!)

#### The Algorithm (Pseudocode)

```
CONFIGURATION:
  NUM_LEVELS = 5-7        # Number of bid levels per side
  LEVEL_SPACING = $0.02   # Price gap between levels
  TOP_SPREAD = $0.01-0.02 # Distance from market for top bid
  SIZE_PER_LEVEL = 24     # Shares per order

MAIN LOOP (runs every ~500ms):

  1. GET MARKET STATE
     up_mid = get_mid_price("Up")
     down_mid = get_mid_price("Down")

  2. CALCULATE TOP BID PRICES
     up_top_bid = up_mid - TOP_SPREAD
     down_top_bid = down_mid - TOP_SPREAD

  3. ENFORCE COMBINED < $1.00
     if up_top_bid + down_top_bid >= 0.98:
         # Scale down both bids proportionally
         scale = 0.97 / (up_top_bid + down_top_bid)
         up_top_bid *= scale
         down_top_bid *= scale

  4. GENERATE BID LADDER
     up_bids = [up_top_bid - i*LEVEL_SPACING for i in range(NUM_LEVELS)]
     down_bids = [down_top_bid - i*LEVEL_SPACING for i in range(NUM_LEVELS)]

  5. UPDATE ORDERS
     for each level:
         if price changed significantly:
             cancel old order
             place new order
```

**Key:** This is automated - no human can adjust 57 trades/minute manually.

---

### Technique 2: Taker Sells (Simple Rebalancing)

When inventory gets too heavy on one side, they SELL excess shares by hitting others' bids.

```
Example:
  Position before: 150 Up, 100 Down (ratio = 1.5, Up-heavy)
  Action: SELL 25 Up via taker order
  Position after: 125 Up, 100 Down (ratio = 1.25, more balanced)
```

**This trader's rebalancing:**
- Sold 90 times when Up-heavy (avg ratio before sell: 1.10)
- Sold 46 times when Down-heavy (avg ratio before sell: 0.85)

**Cost:** They pay the spread (sell below their buy price), but reduce directional risk.

---

### Technique 3: Atomic Swaps (Efficient Rebalancing)

An atomic swap is a **single blockchain transaction** that:
1. Fills their maker BUY order on one side
2. Executes their taker SELL order on the other side

Both happen atomically - either both succeed or both fail.

#### Why Use Atomic Swaps?

To CONVERT position from one side to the other without execution risk!

```
Example:
  Position before: 150 Up, 100 Down (Up-heavy, ratio = 1.5)

  Atomic swap:
    BUY 24 Down @ $0.56 (maker - their bid gets filled)
    SELL 24 Up @ $0.44 (taker - they hit someone's bid)

  Position after: 126 Up, 124 Down (balanced, ratio = 1.02)

  Net cost: 24 × $0.56 - 24 × $0.44 = $2.88
  Combined price: $0.56 + $0.44 = $1.00 (no arbitrage profit/loss)

  But now they're BALANCED - reduced directional risk!
```

#### Actual Atomic Swap Examples:

| Time | Buy | Sell | Net Effect |
|------|-----|------|------------|
| 20:00:20 | 24 Down @ $0.56 | 24 Up @ $0.44 | Up -24, Down +24 |
| 20:00:22 | 24 Down @ $0.56 | 24 Up @ $0.44 | Up -24, Down +24 |
| 20:00:30 | 24 Down @ $0.60 | 24 Up @ $0.40 | Up -24, Down +24 |
| 20:01:42 | 24 Up @ $0.35 | 24 Down @ $0.65 | Up +24, Down -24 |

**This trader's swaps:**
- 54 swaps: Buy Down + Sell Up (1,125 shares converted)
- 32 swaps: Buy Up + Sell Down (671 shares converted)

More "Buy Down + Sell Up" because early on they accumulated too much Up (when Up was cheap).

---

## 9. Risk Management Framework Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RISK MANAGEMENT FRAMEWORK                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. DYNAMIC BID ADJUSTMENT                                          │
│     • Adjust bid prices as market moves                             │
│     • Keep combined bid < $1.00                                     │
│     • Stay competitive to get fills                                 │
│                                                                     │
│  2. TAKER SELLS                                                     │
│     • Sell excess inventory when one side gets too heavy            │
│     • Costs the spread but reduces directional risk                 │
│     • Simple but expensive                                          │
│                                                                     │
│  3. ATOMIC SWAPS                                                    │
│     • Buy one side + Sell other in same transaction                 │
│     • Converts inventory between outcomes                           │
│     • Combined price = $1.00 (no profit/loss on swap)              │
│     • More efficient than simple sells                              │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GOAL: Keep Up/Down ratio close to 1.0                              │
│     • Maximize shares in "complete sets" (hedged)                   │
│     • Minimize unhedged directional exposure                        │
│     • Profit from buy edge, not from outcome prediction             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Key Takeaways

1. **The profit comes from buying complete sets below $1.00** - not from predicting which side wins.

2. **Timing doesn't matter for profitability** - only the final weighted average price matters.

3. **BUT timing creates RISK** - unbalanced fills create directional exposure.

4. **Risk management is essential** - bid adjustments, taker sells, and atomic swaps keep inventory balanced.

5. **Perfect balance is impossible** - some directional risk is unavoidable in a moving market.

6. **This trader lost money** on this particular market because they ended up with 465 extra Down shares when Up won. But across many markets, the strategy should be profitable on average.

---

## 11. Data Files

- `trades_1767988800.json` - All 816 trades with parsed details
- `market_making_strategy_explained.md` - This document

---

*Analysis based on wallet `0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d` trading on Polymarket BTC Up/Down market, January 9, 2026.*
