# Prediction Markets: Glossary & Quick Reference

## Key Terms

### Market Mechanics

| Term | Definition |
|------|------------|
| **Prediction Market** | Exchange where participants trade contracts based on future event outcomes |
| **Event Contract** | Binary contract paying $1 if outcome occurs, $0 otherwise |
| **YES Share** | Contract betting outcome will happen |
| **NO Share** | Contract betting outcome will not happen |
| **Implied Probability** | Contract price expressed as probability (e.g., $0.60 = 60% chance) |
| **Resolution** | Process of determining market outcome and settling contracts |
| **Settlement** | Distribution of funds to winning positions |
| **Order Book** | List of buy and sell orders at various prices |
| **Spread** | Difference between best bid and best ask prices |
| **Slippage** | Price movement caused by executing a trade |

### Trading Terminology

| Term | Definition |
|------|------------|
| **Maker** | Trader who provides liquidity by placing limit orders |
| **Taker** | Trader who removes liquidity by executing against existing orders |
| **Limit Order** | Order to buy/sell at specific price or better |
| **Market Order** | Order to buy/sell immediately at best available price |
| **Position** | Trader's holding in a particular market |
| **Open Interest** | Total outstanding contracts in a market |
| **Volume** | Total value of contracts traded in a period |
| **Liquidity** | Ease of executing trades without moving price |
| **P&L (Profit & Loss)** | Net gain or loss on trading activity |

### Technology Terms

| Term | Definition |
|------|------------|
| **Smart Contract** | Self-executing code on blockchain that automates trades and settlements |
| **Oracle** | System that brings off-chain data (real-world outcomes) to blockchain |
| **USDC** | USD Coin, a dollar-pegged stablecoin |
| **Polygon** | Ethereum Layer 2 scaling solution (Polymarket's blockchain) |
| **Layer 2 (L2)** | Secondary blockchain built on top of main chain for scalability |
| **Gas Fees** | Transaction costs on blockchain networks |
| **Wallet** | Software to store and manage cryptocurrency |
| **DeFi** | Decentralized Finance - blockchain-based financial services |

### Regulatory Terms

| Term | Definition |
|------|------------|
| **CFTC** | Commodity Futures Trading Commission (US federal regulator) |
| **DCM** | Designated Contract Market (CFTC license type) |
| **DCO** | Derivatives Clearing Organization (CFTC clearing license) |
| **CEA** | Commodity Exchange Act (primary US law governing commodities) |
| **No-Action Letter** | CFTC letter stating it won't take enforcement action |
| **KYC** | Know Your Customer - identity verification requirements |
| **AML** | Anti-Money Laundering - regulations preventing illicit finance |

### Analysis Terms

| Term | Definition |
|------|------------|
| **Brier Score** | Measure of forecast accuracy (0 = perfect, 0.25 = random) |
| **Calibration** | How well predictions match actual outcome frequencies |
| **Wisdom of Crowds** | Aggregated predictions often outperform individuals |
| **Wash Trading** | Artificially inflating volume by trading with oneself |
| **Arbitrage** | Profiting from price differences across markets |

---

## Platform Quick Reference

### Polymarket

| Attribute | Value |
|-----------|-------|
| Type | Decentralized prediction market |
| Blockchain | Polygon (Ethereum L2) |
| Currency | USDC |
| Fees | None |
| US Access | Geo-blocked |
| Resolution | UMA oracle |
| 2025 Valuation | $8-15 billion |
| Key Investor | ICE (NYSE owner) - $2B |

### Kalshi

| Attribute | Value |
|-----------|-------|
| Type | CFTC-regulated DCM |
| Blockchain | None (traditional) |
| Currency | USD |
| Fees | 0.7-3.5% |
| US Access | Yes |
| Resolution | Centralized |
| 2025 Valuation | $11 billion |
| Key Investors | Paradigm, Sequoia, CapitalG |

### PredictIt

| Attribute | Value |
|-----------|-------|
| Type | Academic research market |
| Operator | Victoria University of Wellington |
| Currency | USD |
| Position Limit | $850 per contract |
| Trader Limit | 5,000 per market |
| Fees | 10% profit + 5% withdrawal |
| Status | Received DCM/DCO approval (Sept 2025) |

### Metaculus

| Attribute | Value |
|-----------|-------|
| Type | Reputation-based forecasting |
| Currency | Points (no real money) |
| Focus | Science, AI, long-term |
| Funding | $5.5M (Open Philanthropy) |
| Track Record | Brier score 0.151 (all questions) |

---

## Key Statistics (2025)

### Market Size

| Metric | Value |
|--------|-------|
| Decentralized prediction market (2024) | $1.4 billion |
| Combined Polymarket + Kalshi annualized | ~$40 billion |
| Projected 2035 (aggressive) | $95.5 billion |
| Industry CAGR | 45-47% |

### Platform Metrics

| Platform | 2024 Volume | Monthly Active Traders |
|----------|-------------|------------------------|
| Polymarket | ~$9 billion | 314,500 (Dec 2024) |
| Kalshi | $4.47 billion (Q3 2025) | Not disclosed |

### Trading Demographics

| Metric | Value |
|--------|-------|
| Polymarket wallets with PnL > $1K | 0.51% |
| Polymarket whale accounts (>$50K) | 1.74% |
| Estimated wash trading (Polymarket) | 20-60% |

---

## Regulatory Status by Jurisdiction

### United States

| State/Agency | Status |
|--------------|--------|
| CFTC (Federal) | Favorable - Kalshi DCM approved |
| Nevada | Cease-and-desist issued |
| Massachusetts | AG lawsuit pending |
| Connecticut | Cease-and-desist issued |
| Maryland | Lawsuit (38 states amicus) |
| 7+ states | Various enforcement actions |

### International

| Country | Status |
|---------|--------|
| France | Blocked |
| Belgium | Banned |
| Poland | Banned |
| Italy | Banned |
| Switzerland | Blocklisted |
| Singapore | Blocked |
| Germany | Accessible |
| Spain | Accessible |
| UK | Gambling license required |

---

## UMA Oracle Resolution Process

```
Step 1: Market ends
        │
        ▼
Step 2: Proposer submits outcome + bond
        │
        ▼
Step 3: Challenge period (2 hours for Polymarket)
        │
        ├─── No dispute ──► Outcome accepted
        │
        └─── Disputed ──► Goes to DVM
                            │
                            ▼
                     UMA tokenholders vote (48-96 hrs)
                            │
                            ▼
                     Majority determines outcome
```

---

## Fee Comparison

| Platform | Trading Fee | Settlement Fee | Withdrawal Fee |
|----------|-------------|----------------|----------------|
| Polymarket | 0% | 0% | Gas only |
| Kalshi | 0.7-3.5% | 0% | 0% |
| PredictIt | 0% | 10% of profits | 5% |
| Sportsbooks | 5-10% vig | N/A | Varies |

---

## Accuracy Benchmarks

### Forecasting Performance

| Method | Strength | Weakness |
|--------|----------|----------|
| Prediction Markets | Real-time, incentivized | Manipulation risk |
| Polls | Methodological rigor | Slow, response bias |
| Expert Judgment | Domain expertise | Overconfidence |
| Quantitative Models | Systematic | Assumption-dependent |
| Combined | Best accuracy | Complexity |

### Historical Data

| Comparison | Finding |
|------------|---------|
| Markets vs Polls (100 days) | Markets closer 74% of time |
| Long-horizon forecasts | Markets significantly better |
| Short-horizon (1-7 days) | Both accurate |
| Combined methods | Outperforms any single method |

---

## Key Dates Timeline

| Date | Event |
|------|-------|
| 1988 | Iowa Electronic Markets launched |
| 2014 | PredictIt launched with CFTC no-action letter |
| 2015 | Metaculus founded |
| 2018 | Kalshi founded |
| 2020 | Polymarket launched; Kalshi approved as DCM |
| Aug 2022 | CFTC withdraws PredictIt no-action letter |
| July 2023 | Fifth Circuit rules for PredictIt |
| Sept 2024 | DC District Court rules for Kalshi on elections |
| Oct 2024 | DC Circuit denies CFTC stay |
| Nov 2024 | France, Switzerland block Polymarket |
| Jan 2025 | Singapore blocks Polymarket |
| March 2025 | Nevada issues cease-and-desist |
| May 2025 | CFTC drops Kalshi appeal |
| Sept 2025 | Massachusetts AG sues Kalshi; PredictIt gets DCM/DCO |
| Oct 2025 | ICE invests $2B in Polymarket |
| Nov 2025 | Kalshi raises $1B at $11B valuation; DraftKings acquires Railbird |
| Dec 2025 | CFTC issues no-action letters to Polymarket, PredictIt, others |

---

## Quick Formulas

### Implied Probability
```
Implied Probability = Contract Price
Example: YES at $0.65 = 65% probability
```

### Expected Value
```
EV = (Probability × Payout) - Cost
Example:
- Buy YES at $0.40
- True probability = 50%
- EV = (0.50 × $1.00) - $0.40 = +$0.10
```

### Arbitrage Check
```
If YES price + NO price < $1.00:
  Buy both = guaranteed profit of ($1.00 - YES - NO)

If YES price + NO price > $1.00:
  Sell both (if possible) = guaranteed profit
```

### Brier Score
```
Brier Score = (1/N) × Σ(prediction - outcome)²
- prediction = probability assigned (0 to 1)
- outcome = 1 if occurred, 0 if not
- Lower = better (0 = perfect)
```

---

## Resources

### Official Platforms
- Polymarket: polymarket.com
- Kalshi: kalshi.com
- PredictIt: predictit.org
- Metaculus: metaculus.com

### Data & Analytics
- Token Terminal: tokenterminal.com/explorer/projects/polymarket
- Polymarket Analytics: polymarketanalytics.com
- Dune Analytics: dune.com

### Research
- UMA Documentation: docs.uma.xyz
- Academic studies: Google Scholar "prediction markets accuracy"
- CFTC: cftc.gov

### News
- The Block: theblock.co
- CoinDesk: coindesk.com
- Legal: various law firm alerts on prediction market regulation
