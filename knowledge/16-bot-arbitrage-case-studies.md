# Prediction Markets: Bot & Arbitrage Case Studies

## Executive Summary

**Yes, automated trading and arbitrage are happening at scale on prediction markets.**

| Metric | Value | Period |
|--------|-------|--------|
| **Total arbitrage profits extracted** | ~$40 million | Apr 2024 - Apr 2025 |
| **Top single arbitrageur profit** | $2.01 million | 4,049 transactions |
| **Top 3 wallets combined profit** | $4.2 million | 10,200+ bets |
| **Best single bot performance** | $313 → $414,000 | 1 month |
| **Market maker daily profits (peak)** | $700-800/day | During 2024 election |
| **AI-powered bot profit** | $2.2 million | 2 months |

---

## Academic Research: IMDEA Networks Study

### Study Overview

**Title**: "Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets"

**Authors**: Oriol Saguillo, Vahid Ghafouri, Lucianna Kiffer, Guillermo Suarez-Tangil (IMDEA Networks Institute)

**Funding**: Flashbots Research Proposal FRP-51

**Published**: 2025 (arXiv:2508.03474)

### Methodology

| Parameter | Value |
|-----------|-------|
| Conditions analyzed | 17,218 |
| Markets analyzed | 10,237 |
| Total bets scanned | 86 million |
| Time period | April 1, 2024 - April 1, 2025 |
| LLM used | DeepSeek-R1-Distill-Qwen-32B |
| Profit threshold | >$0.05 per dollar |

### Key Findings

#### Profit by Arbitrage Type

| Strategy | Profit Extracted |
|----------|------------------|
| Single condition (long) | $5.9 million |
| Single condition (short) | $4.7 million |
| Multi-condition (YES) | $11.1 million |
| Multi-condition (NO) | $17.3 million |
| Cross-market arbitrage | ~$95,000 |
| **TOTAL** | **~$40 million** |

#### Market Efficiency Metrics

- **Median profit**: $0.60 per dollar invested
- **Implication**: Significant pricing mismatches exist

#### Top Arbitrageur Profile

| Metric | Value |
|--------|-------|
| Total profit | $2,009,631.76 |
| Transactions | 4,049 |
| Average per trade | ~$496 |
| Behavior | Bot-like efficiency |

#### Topic Distribution

| Category | Arbitrage Characteristic |
|----------|-------------------------|
| **Politics (US Election)** | Dominated realized profits |
| **Sports** | Consistent opportunities, lower exploitation |
| **Crypto** | High-frequency opportunities |

### Research Conclusions

1. **Bot dominance**: Top performers show "bot-like" execution patterns
2. **Politics most profitable**: US election markets generated largest profits
3. **Execution risk exists**: Non-atomic arbitrage creates partial fill risk
4. **Market inefficiencies persist**: Significant mispricings remain exploitable

---

## Case Study 1: The $313 → $414,000 Bot

### Profile

| Attribute | Details |
|-----------|---------|
| **Starting capital** | $313 |
| **Final value** | $414,000 |
| **Time period** | 1 month |
| **Win rate** | 98% |
| **Markets traded** | BTC, ETH, SOL 15-minute up/down |
| **Bet size** | $4,000-$5,000 per trade |

### Strategy: Latency Arbitrage

```
┌─────────────────────────────────────────────────────────────┐
│              LATENCY ARBITRAGE MECHANISM                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   BINANCE/COINBASE                     POLYMARKET           │
│   ┌──────────────┐                     ┌──────────────┐     │
│   │ BTC moves    │                     │ 15-min market│     │
│   │ up 0.5%      │                     │ still at     │     │
│   │ CONFIRMED    │                     │ 50/50 odds   │     │
│   └──────┬───────┘                     └──────┬───────┘     │
│          │                                    │              │
│          │     ┌────────────────────┐        │              │
│          └────►│  BOT DETECTS LAG   │◄───────┘              │
│                │                    │                        │
│                │  Real probability: │                        │
│                │  ~85% BTC up       │                        │
│                │                    │                        │
│                │  Polymarket price: │                        │
│                │  ~50% BTC up       │                        │
│                │                    │                        │
│                │  EDGE: 35%         │                        │
│                └─────────┬──────────┘                        │
│                          │                                   │
│                          ▼                                   │
│                ┌────────────────────┐                        │
│                │   BUY YES at $0.50 │                        │
│                │   Expected value:  │                        │
│                │   $0.85            │                        │
│                │   Profit: $0.35    │                        │
│                └────────────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Insight

> "Its secret is not predicting market direction. Rather, it exploits a tiny window where Polymarket prices lag confirmed spot momentum on exchanges like Binance and Coinbase."

### Why It Worked

1. **Information asymmetry**: Polymarket prices updated slower than spot exchanges
2. **High frequency**: Many small bets compound quickly
3. **Near-certainty bets**: Only entered when probability mismatch was extreme
4. **Automation**: Speed impossible for humans to replicate

### Polymarket's Response

Polymarket introduced **dynamic taker fees** on 15-minute crypto markets:
- Fee highest at 50% odds (~3.15%)
- Designed to eliminate latency arbitrage profit margin
- Only applies to short-duration crypto markets

---

## Case Study 2: @defiance_cr Market Making Bot

### Profile

| Attribute | Details |
|-----------|---------|
| **Operator** | @defiance_cr (pseudonymous) |
| **Strategy** | Automated market making |
| **Peak profit** | $700-800/day |
| **Status** | Shut down, code open-sourced |
| **Platform** | Polymarket |

### Strategy Details

```python
# Simplified logic from defiance_cr's approach

def select_markets():
    """
    Find markets with:
    - Low volatility (stable prices)
    - High liquidity rewards (Polymarket incentives)
    - Good spread opportunity
    """
    for market in all_markets:
        volatility = analyze_volatility(market, timeframes=[3h, 24h, 7d, 30d])
        rewards = get_liquidity_rewards(market)
        spread = get_current_spread(market)

        if volatility < THRESHOLD and rewards > MIN_REWARD:
            yield market

def market_make(market):
    """
    Place orders on both sides, capture spread + rewards
    """
    midpoint = get_midpoint(market)

    # Place bid slightly below midpoint
    place_order(side=BUY, price=midpoint - SPREAD/2)

    # Place ask slightly above midpoint
    place_order(side=SELL, price=midpoint + SPREAD/2)

    # Profit = spread captured + LP rewards
```

### Profitability Formula

```
Daily Profit = (Spread Captured × Volume) + LP Rewards - Losses from Adverse Selection

At peak:
- Multiple markets quoted simultaneously
- $200-800/day depending on volatility
- Scalable across dozens of markets
```

### Why He Stopped

1. **LP rewards decreased** after 2024 election
2. **Lower volatility** = fewer opportunities
3. **Chose to open-source** the code (poly-maker on GitHub)

### Market Landscape Insight

> "There were only 3-4 serious liquidity providers on the platform, and most were doing it manually. When active, there were maybe one or two other bots. The space is incredibly underdeveloped compared to traditional crypto markets."

---

## Case Study 3: AI-Powered $2.2M Bot

### Profile

| Attribute | Details |
|-----------|---------|
| **Profit** | $2.2 million |
| **Time period** | ~60 days |
| **Strategy** | AI probability models |
| **Data sources** | News + social data |
| **Operator** | Anonymous (profiled by Igor Mikerin) |

### Strategy: Ensemble AI Models

```
┌─────────────────────────────────────────────────────────────┐
│              AI-POWERED TRADING SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   DATA SOURCES                                               │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │    News     │  │   Social    │  │   Market    │        │
│   │   Feeds     │  │   Media     │  │    Data     │        │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│          │                │                │                │
│          └────────────────┼────────────────┘                │
│                           │                                 │
│                           ▼                                 │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              ENSEMBLE LLM LAYER                      │  │
│   │                                                       │  │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │  │
│   │  │  GPT-4  │ │ Claude  │ │DeepSeek │ │ Gemini  │    │  │
│   │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘    │  │
│   │       └───────────┼───────────┼───────────┘          │  │
│   │                   │           │                       │  │
│   │                   ▼           ▼                       │  │
│   │            ┌─────────────────────┐                    │  │
│   │            │ Consensus Probability│                    │  │
│   │            │ P(event) = 0.73      │                    │  │
│   │            └─────────────────────┘                    │  │
│   └─────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              TRADING DECISION                        │  │
│   │                                                       │  │
│   │   If AI_probability > Market_price + threshold:      │  │
│   │       BUY YES                                        │  │
│   │   If AI_probability < Market_price - threshold:      │  │
│   │       BUY NO                                         │  │
│   │                                                       │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Capabilities

1. **News classification**: Categorize headlines by market impact
2. **Sentiment parsing**: Extract bullish/bearish signals
3. **Event probability estimation**: Generate probability forecasts
4. **Real-time execution**: Trade on mispricings immediately

---

## Case Study 4: Gabagool Binary Arbitrage

### Profile

| Attribute | Details |
|-----------|---------|
| **Trader** | "Gabagool" (pseudonymous) |
| **Strategy** | Binary market arbitrage |
| **Example profit** | $58.52 (single trade) |
| **Markets** | 15-minute BTC up/down |

### Strategy Explanation

**Key Principle**: Never predict direction, exploit mispricing

```
Market: "Will BTC go up in next 15 minutes?"

Step 1: Monitor YES and NO prices

Step 2: Wait for mispricing
         YES = $0.48
         NO  = $0.486
         Combined = $0.966

Step 3: Buy BOTH
         Cost: $0.966
         Guaranteed payout: $1.00

Step 4: Profit
         $1.00 - $0.966 = $0.034 per share

On larger position:
         1,722 shares × $0.034 = $58.52
```

### Why It Works

- Markets temporarily misprice due to order flow imbalances
- High-frequency markets have more mispricings
- Automation catches opportunities humans miss
- Risk-free if both sides execute

---

## Case Study 5: Whale-Following Alert Bot ($75K)

### Profile

| Attribute | Details |
|-----------|---------|
| **Profit** | $75,000 |
| **Key trade** | Maduro arrest bet |
| **Strategy** | Whale tracking + alerts |
| **Execution** | Semi-automated (alerts + manual decisions) |

### Strategy: Insider Detection

```
┌─────────────────────────────────────────────────────────────┐
│              WHALE-FOLLOWING ALERT SYSTEM                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   MONITORING LAYER                                           │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Scan Polymarket API continuously                    │   │
│   │  Track all wallet addresses                          │   │
│   │  Monitor bet sizes and patterns                      │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│   PATTERN DETECTION                                          │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Triggers:                                           │   │
│   │  • Large unusual bets (>$10K)                       │   │
│   │  • Known whale wallet activity                       │   │
│   │  • Sudden volume spikes                              │   │
│   │  • Coordinated multi-wallet buying                   │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│   ALERT + HUMAN DECISION                                     │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Alert sent → Human reviews → Manual trade decision │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Maduro Trade Example

1. **Detection**: Bot flagged unusual large bets on "Maduro captured"
2. **Analysis**: Pattern suggested potential insider knowledge
3. **Decision**: Human reviewed and decided to follow
4. **Outcome**: Bet paid off → $75K profit
5. **Original stake**: $2,000

---

## Open Source Bot Ecosystem

### Available GitHub Projects

| Repository | Strategy | Language |
|------------|----------|----------|
| **poly-maker** (warproxxx) | Market making | Python |
| **Polymarket-Kalshi-Arbitrage-bot** (terauss) | Cross-platform arbitrage | TypeScript |
| **polymarket-kalshi-btc-arbitrage-bot** (CarlosIbCu) | BTC market arbitrage | Python |
| **Polymarket-spike-bot-v1** (Trust412) | Spike detection | Python |
| **polymarket-copy-trading-bot** (multiple) | Whale following | TypeScript |
| **Polymarket/agents** (Official) | AI agent framework | Python |

### Typical Bot Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 POLYMARKET BOT ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                   DATA LAYER                         │   │
│   │  • Polymarket CLOB API (REST + WebSocket)           │   │
│   │  • Kalshi API (for cross-platform)                  │   │
│   │  • External price feeds (Binance, Coinbase)         │   │
│   │  • News APIs / Social feeds                         │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                 STRATEGY LAYER                       │   │
│   │  • Arbitrage detection algorithms                   │   │
│   │  • Price comparison logic                           │   │
│   │  • AI/ML probability models                         │   │
│   │  • Risk management rules                            │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                EXECUTION LAYER                       │   │
│   │  • Order creation (py-clob-client)                  │   │
│   │  • Position management                               │   │
│   │  • Wallet/key management                            │   │
│   │  • Error handling + retry logic                     │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │               MONITORING LAYER                       │   │
│   │  • P&L tracking                                      │   │
│   │  • Alert systems                                     │   │
│   │  • Logging + analytics                               │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Profitability Analysis

### Who's Actually Making Money?

| Trader Type | Estimated % Profitable | Typical Returns |
|-------------|------------------------|-----------------|
| Sophisticated bots | 80-90% | High |
| Semi-automated (alerts) | 30-40% | Medium |
| Manual retail traders | ~16.8% | Low/Negative |

### Profit Distribution

```
┌─────────────────────────────────────────────────────────────┐
│              POLYMARKET PROFIT DISTRIBUTION                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Top 0.51%                                                  │
│   ┌──────┐                                                   │
│   │██████│ PnL > $1,000                                     │
│   └──────┘                                                   │
│                                                              │
│   Top 1.74%                                                  │
│   ┌────────────┐                                            │
│   │████████████│ Whale accounts (volume > $50K)             │
│   └────────────┘                                            │
│                                                              │
│   Top 16.8%                                                  │
│   ┌──────────────────────────┐                              │
│   │██████████████████████████│ Any net profit               │
│   └──────────────────────────┘                              │
│                                                              │
│   Bottom 83.2%                                               │
│   ┌────────────────────────────────────────────────────┐    │
│   │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│    │
│   │              Break-even or Loss                     │    │
│   └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Strategy Profitability Comparison

| Strategy | Difficulty | Capital Required | Expected Return | Competition |
|----------|------------|------------------|-----------------|-------------|
| Latency arbitrage | High | $10K+ | High (diminishing) | Increasing |
| Cross-platform arb | Medium | $20K+ | Medium | Low |
| Market making | Medium | $10K+ | Medium | Low |
| AI sentiment | High | $5K+ | Variable | Medium |
| Whale following | Low | $1K+ | Variable | High |
| Manual trading | Low | Any | Negative (average) | N/A |

---

## Challenges & Risks

### Technical Risks

| Risk | Description |
|------|-------------|
| **Execution failure** | Partial fills, network issues |
| **API rate limits** | Getting blocked from platform |
| **Smart contract bugs** | Potential fund loss |
| **Oracle manipulation** | Incorrect resolutions |

### Market Risks

| Risk | Description |
|------|-------------|
| **Edge decay** | Strategies become crowded |
| **Fee introduction** | Platform response to bots |
| **Liquidity withdrawal** | Markets dry up |
| **Black swan events** | Unexpected outcomes |

### Competitive Risks

| Risk | Description |
|------|-------------|
| **Faster bots** | Being front-run |
| **Whale manipulation** | Large players moving markets |
| **Copy trading** | Others following your trades |

---

## Key Takeaways

### Is Bot Trading Viable?

**Yes, but with caveats:**

1. **Arbitrage is real**: $40M extracted in one year proves opportunities exist
2. **Bots dominate**: Top performers are automated
3. **Edges diminish**: Polymarket actively closing exploits (fees)
4. **Capital matters**: Meaningful returns require $10K+ typically
5. **Technical skills required**: Not plug-and-play

### Best Opportunities (2025-2026)

| Opportunity | Why |
|-------------|-----|
| **Cross-platform arbitrage** | Low competition, regulatory fragmentation |
| **Market making** | Few serious players, underdeveloped |
| **AI-powered trading** | Information edges still exist |
| **New market categories** | Sports expansion = new opportunities |

### Declining Opportunities

| Opportunity | Why Declining |
|-------------|---------------|
| **15-min crypto latency arb** | Fees introduced |
| **Simple YES/NO arb** | More crowded |
| **Whale following (obvious)** | Whales using multiple wallets |

---

## Resources

### Research Papers
- [IMDEA Arbitrage Study](https://arxiv.org/html/2508.03474v1) - Primary academic research

### Tools
- [Polymarket Analytics](https://polymarketanalytics.com) - Trader leaderboards
- [PolyTrack](https://polytrackhq.app) - Whale tracking
- [Dune Analytics](https://dune.com) - On-chain queries

### Open Source
- [Polymarket/agents](https://github.com/Polymarket/agents) - Official AI agent framework
- [py-clob-client](https://github.com/Polymarket/py-clob-client) - Official Python SDK
- [poly-maker](https://github.com/warproxxx/poly-maker) - Market making bot

### News & Analysis
- [BeInCrypto](https://beincrypto.com) - Bot coverage
- [DL News](https://www.dlnews.com) - Research coverage
- [The Oracle](https://news.polymarket.com) - Polymarket newsletter
