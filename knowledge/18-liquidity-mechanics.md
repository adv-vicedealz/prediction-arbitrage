# Prediction Markets: Liquidity Mechanics Deep-Dive

## Order Book Architecture

### CLOB vs AMM

Polymarket transitioned from **AMM (Automated Market Maker)** to **CLOB (Central Limit Order Book)** in late 2022.

| Feature | AMM | CLOB |
|---------|-----|------|
| **Price setting** | Algorithm (x*y=k) | Traders |
| **Liquidity** | Pool-based | Order book |
| **Slippage** | High on large orders | Lower with depth |
| **Market making** | Passive LPs | Active market makers |
| **Capital efficiency** | Lower | Higher |

### Polymarket's Hybrid Model

```
┌─────────────────────────────────────────────────────────────┐
│              POLYMARKET HYBRID ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   PRIMARY: CENTRAL LIMIT ORDER BOOK (CLOB)                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                                                       │   │
│   │  OFF-CHAIN                    ON-CHAIN               │   │
│   │  ┌──────────────┐             ┌──────────────┐       │   │
│   │  │  Order       │             │  Settlement  │       │   │
│   │  │  Matching    │────────────►│  Execution   │       │   │
│   │  │  Engine      │             │  (Polygon)   │       │   │
│   │  └──────────────┘             └──────────────┘       │   │
│   │                                                       │   │
│   │  Benefits:                                            │   │
│   │  • Fast matching (off-chain)                         │   │
│   │  • Trustless settlement (on-chain)                   │   │
│   │  • Gas-efficient                                      │   │
│   │                                                       │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
│   BACKUP: FIXED PRODUCT MARKET MAKER (FPMM)                 │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Deployed per market via factory contract            │   │
│   │  Provides baseline liquidity                         │   │
│   │  Used when CLOB liquidity insufficient               │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Order Book Mechanics

### Unified Book Structure

**Key Innovation**: YES and NO share a unified order book.

```
Because YES + NO = $1.00 (always):

BUY YES @ $0.60  =  SELL NO @ $0.40
SELL YES @ $0.65 =  BUY NO @ $0.35

This creates:
• Deeper liquidity (orders visible from both sides)
• Tighter spreads
• More efficient price discovery
```

### Order Book Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    ORDER BOOK EXAMPLE                        │
│                  Market: "Trump Wins 2024"                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  BIDS (Buy YES)              ASKS (Sell YES)                │
│  ──────────────              ───────────────                │
│                                                              │
│  $0.58  │████████ 2,500      $0.62  │██████ 1,800           │
│  $0.57  │██████ 1,800        $0.63  │████████ 2,200         │
│  $0.56  │████ 1,200          $0.64  │██████████ 3,000       │
│  $0.55  │██████████ 3,500    $0.65  │████ 1,500             │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│  Spread: $0.04 (4 cents)                                    │
│  Midpoint: $0.60                                            │
│  Best Bid: $0.58 | Best Ask: $0.62                         │
│                                                              │
│  EQUIVALENT NO BOOK:                                        │
│  Best Bid NO: $0.38 | Best Ask NO: $0.42                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Order Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Limit** | Execute at specific price or better | Market making, precise entry |
| **Market** | Execute immediately at best available | Quick entry/exit |
| **FOK** | Fill or Kill - all or nothing | Large orders |
| **GTC** | Good Till Cancelled | Long-term positions |

---

## Liquidity Rewards Program

### Overview

Polymarket incentivizes liquidity provision through daily rewards distributed to market makers.

### How Rewards Work

```
┌─────────────────────────────────────────────────────────────┐
│              LIQUIDITY REWARDS MECHANICS                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   FACTORS DETERMINING YOUR REWARD:                          │
│                                                              │
│   1. PROXIMITY TO MIDPOINT                                  │
│      ┌─────────────────────────────────────────────────┐    │
│      │  Closer to midpoint = Higher reward             │    │
│      │                                                  │    │
│      │  Midpoint: $0.50                                │    │
│      │  Your order @ $0.48: HIGH reward               │    │
│      │  Your order @ $0.40: LOWER reward              │    │
│      │  Your order @ $0.30: NO reward (outside max)   │    │
│      └─────────────────────────────────────────────────┘    │
│                                                              │
│   2. ORDER SIZE                                              │
│      ┌─────────────────────────────────────────────────┐    │
│      │  Larger orders = More reward (with min cutoff) │    │
│      │                                                  │    │
│      │  Orders below min size: No reward              │    │
│      │  Larger orders: Proportionally more            │    │
│      └─────────────────────────────────────────────────┘    │
│                                                              │
│   3. TWO-SIDED DEPTH                                        │
│      ┌─────────────────────────────────────────────────┐    │
│      │  Having orders on BOTH sides boosts reward     │    │
│      │                                                  │    │
│      │  Exception: If midpoint < $0.10, you MUST     │    │
│      │  have orders on both sides to qualify          │    │
│      └─────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Reward Parameters (Per Market)

| Parameter | Description | Where to Find |
|-----------|-------------|---------------|
| **Max Spread** | Max distance from midpoint for eligibility | Order book UI (blue lines) |
| **Min Size** | Minimum order size for eligibility | Market details |
| **Daily Reward Pool** | Total USDC distributed daily | Market details |

### Example Calculation

```
Market: "Will X happen?"
Daily reward pool: $300
Max spread: 3 cents
Your orders: $0.48 bid (500 shares), $0.52 ask (500 shares)
Midpoint: $0.50

Your score factors:
• Proximity: 2 cents from mid (good)
• Size: 500 shares each side
• Two-sided: Yes (bonus)

If total market maker score = 10,000
Your score = 800

Your daily reward = ($300 × 800) / 10,000 = $24
```

### Payout Details

| Attribute | Value |
|-----------|-------|
| Frequency | Daily (midnight UTC) |
| Minimum payout | $1 |
| Payment method | Direct to wallet |
| Tracking | Portfolio page history |

---

## Maker Rebates Program

### For 15-Minute Crypto Markets

Since taker fees were introduced on short-duration crypto markets:

```
TAKER FEES COLLECTED → 100% REDISTRIBUTED AS MAKER REBATES

Your rebate = Your maker volume / Total maker volume × Total fees collected
```

### Fee Structure (15-min markets)

| Odds Range | Taker Fee |
|------------|-----------|
| Near 50% | ~3.15% |
| Near 0% or 100% | Lower |

**Purpose**: Eliminate latency arbitrage while rewarding legitimate LPs.

---

## Market Making Strategy

### Basic Market Making

```python
class SimpleMarketMaker:
    def __init__(self, client, token_id):
        self.client = client
        self.token_id = token_id
        self.spread = 0.04  # 4 cents
        self.size = 100     # shares per side

    def get_fair_value(self):
        """Estimate fair price (midpoint or model)"""
        book = self.client.get_order_book(self.token_id)
        best_bid = float(book['bids'][0]['price'])
        best_ask = float(book['asks'][0]['price'])
        return (best_bid + best_ask) / 2

    def update_quotes(self):
        """Cancel old orders, place new ones"""
        # Cancel existing
        self.client.cancel_all()

        fair = self.get_fair_value()

        # Place bid
        bid_price = fair - (self.spread / 2)
        self.client.create_and_post_order(
            token_id=self.token_id,
            price=bid_price,
            size=self.size,
            side=BUY
        )

        # Place ask
        ask_price = fair + (self.spread / 2)
        self.client.create_and_post_order(
            token_id=self.token_id,
            price=ask_price,
            size=self.size,
            side=SELL
        )

    def run(self, interval=10):
        """Main loop"""
        while True:
            try:
                self.update_quotes()
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(interval)
```

### Advanced: Inventory Management

```python
class InventoryAwareMarketMaker:
    def __init__(self, client, token_id, max_inventory=1000):
        self.client = client
        self.token_id = token_id
        self.max_inventory = max_inventory
        self.base_spread = 0.04
        self.base_size = 100

    def get_inventory(self):
        """Get current position"""
        positions = self.client.get_positions()
        for p in positions:
            if p['token_id'] == self.token_id:
                return float(p['size'])
        return 0

    def calculate_skew(self):
        """Skew quotes based on inventory"""
        inventory = self.get_inventory()
        inventory_pct = inventory / self.max_inventory

        # Skew to reduce inventory
        # Positive inventory → lower bids, higher asks
        skew = inventory_pct * 0.02  # max 2 cent skew
        return skew

    def update_quotes(self):
        fair = self.get_fair_value()
        skew = self.calculate_skew()

        bid_price = fair - (self.base_spread / 2) - skew
        ask_price = fair + (self.base_spread / 2) - skew

        # Reduce size if inventory is high
        inventory_factor = max(0.2, 1 - abs(self.get_inventory() / self.max_inventory))
        size = self.base_size * inventory_factor

        self.place_orders(bid_price, ask_price, size)
```

### Key Metrics to Monitor

| Metric | Formula | Target |
|--------|---------|--------|
| **Spread P&L** | Asks filled × ask price - Bids filled × bid price | Positive |
| **Inventory risk** | Position × price volatility | Minimize |
| **Reward earnings** | Daily LP rewards | Maximize |
| **Fill rate** | Orders filled / orders placed | 20-50% |

---

## Order Book Analysis

### Depth Analysis

```python
def analyze_depth(order_book, levels=5):
    """Analyze order book depth"""
    bids = order_book['bids'][:levels]
    asks = order_book['asks'][:levels]

    bid_depth = sum(float(b['size']) * float(b['price']) for b in bids)
    ask_depth = sum(float(a['size']) * float(a['price']) for a in asks)

    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

    return {
        'bid_depth_usd': bid_depth,
        'ask_depth_usd': ask_depth,
        'imbalance': imbalance,  # Positive = more bids, Negative = more asks
        'spread': float(asks[0]['price']) - float(bids[0]['price'])
    }
```

### Spread Monitoring

```python
def calculate_spread_metrics(book):
    best_bid = float(book['bids'][0]['price'])
    best_ask = float(book['asks'][0]['price'])

    spread = best_ask - best_bid
    midpoint = (best_ask + best_bid) / 2
    spread_pct = spread / midpoint * 100

    return {
        'spread_absolute': spread,
        'spread_percent': spread_pct,
        'midpoint': midpoint,
        'best_bid': best_bid,
        'best_ask': best_ask
    }
```

---

## Liquidity Dynamics

### What Affects Liquidity?

| Factor | Effect on Liquidity |
|--------|---------------------|
| **Market interest** | High interest → More LPs → Tighter spreads |
| **Volatility** | High volatility → Wider spreads → Less depth |
| **Time to resolution** | Approaching end → Less LP activity |
| **LP reward pool** | Higher rewards → More LPs |
| **Fee structure** | Taker fees → Encourages LP activity |

### Liquidity Cycles

```
┌─────────────────────────────────────────────────────────────┐
│              MARKET LIQUIDITY LIFECYCLE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CREATION → GROWTH → PEAK → DECLINE → RESOLUTION            │
│                                                              │
│     │          │        │        │          │               │
│     ▼          ▼        ▼        ▼          ▼               │
│                                                              │
│  Low LP    More LPs   Max LP   LPs exit   Settlement        │
│  interest  attracted  activity  positions  only              │
│                                                              │
│  Wide      Tighter    Tight    Widening   N/A               │
│  spreads   spreads    spreads  spreads                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Cross-Platform Liquidity

### Polymarket vs Kalshi Liquidity

| Aspect | Polymarket | Kalshi |
|--------|------------|--------|
| **Order book model** | Hybrid CLOB | Traditional CLOB |
| **LP incentives** | Explicit rewards | Spread capture only |
| **Fee structure** | 0% (mostly) | 0.7-3.5% |
| **Settlement** | On-chain (Polygon) | Traditional |
| **Minimum order** | Flexible | Varies |

### Arbitrage Implications

Low liquidity in one platform creates arbitrage opportunities:

```
Example:
Polymarket "Event X": 60% YES (deep liquidity)
Kalshi "Event X": 55% YES (thin liquidity)

Arbitrageur:
• Buy YES on Kalshi @ $0.55
• Sell YES on Polymarket @ $0.60
• Lock in 5% profit (minus fees)

Result: Prices converge, liquidity improves
```

---

## Practical Considerations

### Minimum Capital Requirements

| Strategy | Minimum Capital | Reasoning |
|----------|-----------------|-----------|
| Basic MM (1 market) | $5,000 | Need depth on both sides |
| Multi-market MM | $10,000+ | Spread across markets |
| Arbitrage | $10,000+ | Locked until settlement |
| Whale following | $1,000 | Smaller positions |

### Risk Management

```python
class RiskManager:
    def __init__(self, max_position=5000, max_loss_daily=500):
        self.max_position = max_position
        self.max_loss_daily = max_loss_daily
        self.daily_pnl = 0

    def check_position_limit(self, current_position, new_order_size):
        """Prevent exceeding position limits"""
        if abs(current_position + new_order_size) > self.max_position:
            return False
        return True

    def check_daily_loss(self):
        """Stop trading if daily loss limit hit"""
        if self.daily_pnl < -self.max_loss_daily:
            return False
        return True

    def can_trade(self, current_position, order_size):
        return (
            self.check_position_limit(current_position, order_size) and
            self.check_daily_loss()
        )
```

### Gas Optimization

```python
# Batch operations when possible
def batch_cancel_and_replace(client, old_orders, new_orders):
    """Cancel and replace in minimal transactions"""
    # Cancel all at once
    client.cancel_orders([o['id'] for o in old_orders])

    # Place new orders in batch
    for order in new_orders:
        client.create_and_post_order(**order)
```
