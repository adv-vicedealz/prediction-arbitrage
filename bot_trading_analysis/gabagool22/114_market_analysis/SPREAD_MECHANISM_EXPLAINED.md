# How gabagool22 Actually Captures Spread

## Your Question
> If I want UP+DOWN < $1.00, I could:
> - Option A: UP at market, DOWN below market
> - Option B: UP below market, DOWN at market
> - Option C: Split discount between both

## The Surprising Answer: NONE OF THE ABOVE

**They post AT market price for BOTH sides!**

The data shows:
- 90% of UP orders are at exactly market price (discount ~$0.00)
- 96% of DOWN orders are at exactly market price (discount ~$0.00)
- When posting both sides: 58% have EQUAL discount (zero)

---

## So How Do They Profit?

### The Key Insight: MAKER vs TAKER Spread

| Order Type | UP Price | DOWN Price | Combined |
|------------|----------|------------|----------|
| **MAKER** (limit order) | $0.5193 | $0.4404 | $0.9597 |
| **TAKER** (market order) | $0.5696 | $0.4997 | $1.0693 |
| **Difference** | $0.05 | $0.06 | **$0.11** |

By being a MAKER instead of TAKER, they save **$0.11 per pair!**

---

## How Order Books Work

```
POLYMARKET ORDER BOOK (simplified)
==================================

         UP TOKEN                    DOWN TOKEN
    ┌─────────────────┐         ┌─────────────────┐
    │ SELL ORDERS     │         │ SELL ORDERS     │
    │ (asks)          │         │ (asks)          │
    │                 │         │                 │
    │ $0.53 - 50 shrs │         │ $0.50 - 50 shrs │
    │ $0.52 - 100 shrs│         │ $0.49 - 100 shrs│ ← ASK price
    │─────────────────│         │─────────────────│
    │ $0.51 - 100 shrs│ ← BID   │ $0.48 - 100 shrs│ ← BID price
    │ $0.50 - 50 shrs │         │ $0.47 - 50 shrs │
    │ BUY ORDERS      │         │ BUY ORDERS      │
    │ (bids)          │         │ (bids)          │
    └─────────────────┘         └─────────────────┘

    Mid-price: $0.515               Mid-price: $0.485

    Combined mid: $0.515 + $0.485 = $1.00
    Combined bid: $0.51 + $0.48 = $0.99 ← WHERE GABAGOOL22 BUYS
```

---

## The Spread Capture Mechanism

### Step 1: Post BUY Limit Orders at BID Price
```
gabagool22 posts:
  - BUY 26 UP at $0.51 (top of bid)
  - BUY 26 DOWN at $0.48 (top of bid)
```

### Step 2: Wait for Sellers to Hit Their Bids
```
When someone wants to SELL UP quickly:
  - They hit gabagool22's $0.51 bid
  - gabagool22 gets UP shares at $0.51
  - True mid-price might be $0.515
  - gabagool22 captured $0.005 spread!
```

### Step 3: Accumulate Both Sides
```
Over time:
  - Accumulate UP shares at avg $0.5193
  - Accumulate DOWN shares at avg $0.4404
  - Combined cost: $0.9597 per pair
```

### Step 4: Wait for Market Resolution
```
At resolution:
  - One side pays $1.00
  - Other side pays $0.00
  - If balanced: Profit = $1.00 - $0.9597 = $0.0403 per pair
```

---

## Why They Don't "Choose" the Price Split

The question "should I discount UP or DOWN more?" misunderstands the mechanism.

**They don't set prices. The market does.**

```
Market shows:          They post:
UP: $0.51/$0.52       BUY UP at $0.51 (bid)
DOWN: $0.48/$0.49     BUY DOWN at $0.48 (bid)

The "discount" comes automatically from:
1. Being on the BID side (not ASK)
2. People selling TO them (not buying from them)
3. The natural bid-ask spread in the market
```

---

## The Real Algorithm

```python
def gabagool22_strategy():
    while market_is_open:
        # 1. Get current order book
        up_bid, up_ask = get_order_book("UP")
        down_bid, down_ask = get_order_book("DOWN")

        # 2. Post at TOP of bid (best price to attract sellers)
        post_buy_limit("UP", price=up_bid, size=26)
        post_buy_limit("DOWN", price=down_bid, size=26)

        # 3. When orders fill, check imbalance
        if up_position >> down_position:
            # Cancel some UP orders, post more DOWN
            rebalance()

        # 4. Repeat every few seconds
        sleep(2)
```

---

## Summary

| Question | Answer |
|----------|--------|
| How to get UP+DOWN < $1? | Post BUY limits at BID prices |
| Who chooses the split? | The MARKET (bid-ask spread) |
| Where's the profit? | MAKER buys cheaper than TAKER |
| How much spread? | ~$0.05-0.06 per share (~5-6%) |
| Total edge per pair | ~$0.04 (4%) |

**The "secret" isn't clever pricing. It's being on the right side of the order book.**
