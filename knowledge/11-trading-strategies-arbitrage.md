# Prediction Markets: Trading Strategies & Arbitrage

## Overview of Profitable Strategies

```
┌─────────────────────────────────────────────────────────────┐
│            PREDICTION MARKET TRADING STRATEGIES              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  ARBITRAGE  │  │   MARKET    │  │INFORMATIONAL│         │
│  │             │  │   MAKING    │  │    EDGE     │         │
│  │• Cross-plat │  │• Bid-ask    │  │• Research   │         │
│  │• Intra-mkt  │  │  spread     │  │• Alt data   │         │
│  │• Combinat-  │  │• Liquidity  │  │• Modeling   │         │
│  │  orial      │  │  provision  │  │• Timing     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ BEHAVIORAL  │  │  EVENT-     │  │    HIGH     │         │
│  │EXPLOITATION │  │   DRIVEN    │  │  FREQUENCY  │         │
│  │             │  │             │  │             │         │
│  │• Longshot   │  │• News       │  │• Bot-based  │         │
│  │  bias       │  │  trading    │  │• Latency    │         │
│  │• Overreact  │  │• Catalyst   │  │  arbitrage  │         │
│  │• Momentum   │  │  plays      │  │• Auto rebal │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Arbitrage Strategies

### Types of Arbitrage

#### A. Single-Market Arbitrage (YES/NO Mispricing)

**Fundamental Property**: YES + NO = $1.00 (guaranteed)

**Opportunity Detection**:
```
If YES ask + NO ask < $1.00:
    Buy both → Guaranteed profit = $1.00 - (YES + NO)

Example:
    YES trading at $0.48
    NO trading at $0.48
    Total cost: $0.96
    Guaranteed return: $1.00
    Profit: $0.04 (4.2% risk-free)
```

**Why It Happens**:
- Temporary liquidity imbalances
- News shock causing one side to move faster
- Low-liquidity markets with wide spreads

#### B. Cross-Platform Arbitrage

**Mechanism**: Exploit price differences between Polymarket, Kalshi, PredictIt

**Example (Sept 2025)**:
- James Talarico Democratic Senate nomination
- Kalshi: 38% probability
- Polymarket: 59% probability
- **Gross arbitrage opportunity: 3.09%**

**Execution**:
```
1. Buy YES on Kalshi at $0.38
2. Buy NO on Polymarket at $0.41 (1 - 0.59)
3. Total cost: $0.79
4. Guaranteed payout: $1.00
5. Gross profit: $0.21 (26.6%)
```

**Challenges**:
- Capital locked until resolution (weeks/months)
- Slight contract language differences
- Settlement timing variations
- Platform counterparty risk

#### C. Combinatorial Arbitrage

**Definition**: Exploit inconsistencies between related markets

**Example**:
```
Market A: "Will Democrats win Senate?" = 55%
Market B: "Will Democrats win 51+ seats?" = 40%
Market C: "Will Democrats win exactly 50 seats?" = 20%

If B + C > A, arbitrage exists:
    40% + 20% = 60% > 55%

    Action: Buy A, Sell B+C (if shorting available)
```

### Arbitrage Returns & Frequency

| Metric | Value |
|--------|-------|
| Typical opportunity size | 0.5-3% |
| Duration before closing | Seconds to minutes |
| Annual profits extracted (2024-2025) | ~$40 million |
| Top 3 wallets profits | $4.2 million |
| Required spread for profitability | >2.5-3% (after fees) |

### Fee Impact on Arbitrage

| Platform | Trading Fee | Settlement Fee | Impact |
|----------|-------------|----------------|--------|
| Polymarket US | 0.01% | 0% | Minimal |
| Polymarket Int'l | 0% | 2% on winnings | Significant |
| Kalshi | ~0.7% | 0% | Moderate |
| PredictIt | 0% | 10% on profit | High |

**Break-even Calculation**:
```
Minimum profitable spread = Fee_A + Fee_B + gas costs

Example (Polymarket Int'l vs Kalshi):
    Minimum spread = 2% + 0.7% + ~0.1% gas = 2.8%
```

---

## 2. Market Making Strategies

### Basic Market Making

**Objective**: Profit from bid-ask spread while managing inventory

```
┌─────────────────────────────────────────────────────────────┐
│                    MARKET MAKING FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   1. Post bid at $0.58 (willing to buy YES)                 │
│   2. Post ask at $0.62 (willing to sell YES)                │
│   3. Spread = $0.04 (4 cents per round-trip)                │
│                                                              │
│   If both sides fill:                                        │
│   • Buy at $0.58, Sell at $0.62                             │
│   • Profit: $0.04 per contract                              │
│                                                              │
│   Risk: Inventory accumulation if market moves              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Advanced Market Making Techniques

**1. Volatility-Adjusted Spreads**
- Widen spreads during high volatility
- Tighten during calm periods
- Reference VIX or event-specific volatility

**2. Order Imbalance Trading**
- Track buy/sell pressure
- Adjust quotes based on flow direction
- Fade extreme moves

**3. Inventory Management**
- Set position limits
- Hedge across related markets
- Reduce size when approaching limits

### Market Making Performance

Research shows optimal market making combines:
1. Pricing based on latest trading price
2. Volatility information integration
3. Order imbalance awareness

**Result**: Increased daily returns vs. naive strategies

---

## 3. Informational Edge Strategies

### The Théo Model (French Whale Case Study)

**Strategy**: Proprietary research + alternative data

**Execution**:
1. Identified "shy voter" effect in traditional polls
2. Discovered "neighbor polling" methodology
3. Commissioned private YouGov poll
4. Accumulated position over months (11 accounts)
5. **Result**: $85M deployed, $48M profit

**Key Insight**:
> "Who are your neighbors voting for?" outperformed "Who are you voting for?"

### Alternative Data Sources

| Data Type | Application |
|-----------|-------------|
| Social sentiment | Gauge public mood shifts |
| Satellite imagery | Verify real-world events |
| Web scraping | Early news detection |
| Private polling | Proprietary probability estimates |
| Insider networks | Industry-specific intelligence |

### Research-Based Trading

**Academic Approach**:
1. Study historical market accuracy
2. Identify systematic biases
3. Build predictive models
4. Trade on model vs. market disagreements

**Example**: Longshot bias exploitation
- Markets systematically overprice low-probability events
- Betting against longshots shows +EV historically
- Average profit betting favorites: -3.64%
- Average profit betting outsiders: -26.08%

---

## 4. Behavioral Exploitation

### Known Biases in Prediction Markets

| Bias | Description | Exploitation |
|------|-------------|--------------|
| **Longshot Bias** | Overvaluing unlikely outcomes | Bet against extreme longshots |
| **Recency Bias** | Overweighting recent events | Fade overreactions |
| **Favorite-Longshot Bias** | Undervaluing favorites | Back heavy favorites |
| **Confirmation Bias** | Seeking confirming info | Trade against consensus |
| **Overconfidence** | Excessive certainty | Buy insurance positions |

### Mean Reversion Trading

**Concept**: Prices tend to revert to fair value after overreaction

```
If price moves >10% in <1 hour without fundamental news:
    Likely overreaction
    Consider counter-trend position
    Set stop-loss at recent extreme
```

---

## 5. Event-Driven Strategies

### News Trading

**Approach**: React faster than market to information

**Challenges**:
- Algorithms often faster than humans
- Need reliable news feeds
- Risk of false signals

### Catalyst Calendar Trading

**Pre-Position for Known Events**:
- Scheduled announcements
- Court rulings
- Election dates
- Economic releases

**Strategy**:
1. Buy volatility before event
2. Or take directional view
3. Exit before/after announcement

---

## 6. High-Frequency & Automated Trading

### Bot Dominance

**Statistics (2024-2025)**:
- Top bot executed 10,200+ bets
- Generated $4.2 million profit
- Average ~$412 per trade
- Dominates arbitrage extraction

### Bot Capabilities

| Function | Description |
|----------|-------------|
| Cross-platform monitoring | Track prices across Polymarket, Kalshi, PredictIt |
| Arbitrage detection | Identify spreads in milliseconds |
| Auto-execution | Trade without human intervention |
| Position management | Rebalance across markets |
| Risk controls | Automatic stop-losses |

### Infrastructure Requirements

```
┌─────────────────────────────────────────────────────────────┐
│              AUTOMATED TRADING STACK                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│   │  Data Feed  │───►│  Strategy   │───►│  Execution  │    │
│   │   Layer     │    │   Engine    │    │   Layer     │    │
│   └─────────────┘    └─────────────┘    └─────────────┘    │
│         │                   │                   │           │
│   • Polymarket API   • Signal gen      • Order routing     │
│   • Kalshi API       • Risk calc       • Position mgmt     │
│   • On-chain data    • Backtest        • P&L tracking      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Open Source Tools

| Tool | Purpose | Link |
|------|---------|------|
| py-clob-client | Polymarket Python SDK | github.com/Polymarket/py-clob-client |
| Arbitrage bots | Cross-platform arb | github.com/terauss/Polymarket-Kalshi-Arbitrage-bot |
| BTC arb bot | Bitcoin market arb | github.com/CarlosIbCu/polymarket-kalshi-btc-arbitrage-bot |

---

## 7. Position Sizing & Risk Management

### Kelly Criterion for Prediction Markets

**Formula**:
```
f* = (bp - q) / b

Where:
    f* = fraction of bankroll to bet
    b = odds received (payout - 1)
    p = probability of winning
    q = probability of losing (1 - p)
```

**Example**:
```
Market price: $0.40 (implied 40%)
Your estimate: 60%
Payout if correct: $1 / $0.40 = 2.5x
b = 1.5 (net of stake)

f* = (1.5 × 0.60 - 0.40) / 1.5
f* = (0.90 - 0.40) / 1.5
f* = 0.33 (33% of bankroll)
```

**Practical Adjustment**: Most traders use fractional Kelly (25-50%) to reduce variance.

### Risk Management Rules

| Rule | Implementation |
|------|----------------|
| Position limits | Max 5-10% of capital per market |
| Correlation awareness | Reduce size on correlated positions |
| Stop-losses | Exit if thesis invalidated |
| Profit targets | Scale out at predetermined levels |
| Time stops | Exit if no movement by deadline |

---

## 8. Whale Behavior Analysis

### Identifying Whale Activity

**On-Chain Signals**:
- Large transactions (>$10K)
- Cluster of related wallets
- Unusual accumulation patterns
- >90% of large orders at prices >$0.95

### Whale Following Strategy

**Caution**: Whales often accumulate before news
- Could be informed (profitable to follow)
- Could be manipulating (costly to follow)

**Due Diligence**:
1. Track wallet history (PolyTrack, Dune)
2. Assess past prediction accuracy
3. Consider thesis behind position
4. Don't blindly copy

---

## 9. Expected Value Framework

### Calculating Edge

```
Expected Value = (Win Probability × Payout) - (Loss Probability × Loss)

Example:
    Buy YES at $0.35
    Estimate true probability: 50%

    EV = (0.50 × $0.65) - (0.50 × $0.35)
    EV = $0.325 - $0.175
    EV = +$0.15 per contract (42.9% ROI expected)
```

### Required Edge for Profitability

| Fee Structure | Minimum Edge Needed |
|---------------|---------------------|
| Zero fees | Any positive edge |
| 1% fee | >1% edge |
| 2% fee | >2% edge |
| 5% fee | >5% edge |

---

## 10. Common Mistakes to Avoid

| Mistake | Consequence | Solution |
|---------|-------------|----------|
| Overconfidence | Oversized positions | Use Kelly criterion |
| Ignoring fees | Negative EV trades | Calculate net returns |
| Correlation blindness | Concentrated risk | Diversify across events |
| FOMO trading | Chasing moved markets | Stick to research |
| Illiquidity ignorance | Slippage on exit | Check order book depth |
| Thesis drift | Holding losing positions | Document entry thesis |

---

## Profitability Reality Check

### Trader Distribution on Polymarket

| Category | % of Traders |
|----------|--------------|
| Profitable (PnL > $1K) | 0.51% |
| Whale accounts | 1.74% |
| Break-even or loss | ~98% |

### Top Performer Statistics

| Metric | Value |
|--------|-------|
| #1 trader total profit | $2.01 million |
| Transactions | 4,049 |
| Average per trade | ~$496 |
| Required: Skill + capital + execution |
