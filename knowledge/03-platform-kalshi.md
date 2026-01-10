# Kalshi: Platform Deep Dive

## Company Overview

| Attribute | Details |
|-----------|---------|
| **Founded** | 2018 |
| **Headquarters** | New York, USA |
| **Type** | CFTC-regulated Designated Contract Market (DCM) |
| **Settlement** | USD (bank transfer, credit card) |
| **Valuation** | $11 billion (Dec 2025) |
| **Total Funding** | ~$1.7 billion |
| **Regulatory Status** | First CFTC-approved prediction market |

## Founders

- **Tarek Mansour** - CEO
- **Luana Lopes Lara** - Co-founder

## Key Metrics (2024-2025)

### Trading Volume
| Period | Volume |
|--------|--------|
| 2024 Presidential Election | $527 million |
| Monthly Volume (Sept 2025) | $1.3 billion |
| Q3 2025 | $4.47 billion |
| Weekly Volume (late 2025) | >$1 billion |
| October 2025 | $4.4 billion |

### Market Expansion
| Metric | Value |
|--------|-------|
| Available Markets | 3,500+ |
| Market Categories | Politics, Sports, Crypto, Climate, Economics, Finance |

## Funding History

| Round | Date | Amount | Valuation | Key Investors |
|-------|------|--------|-----------|---------------|
| Seed | 2019 | - | - | Y Combinator |
| Series A | 2021 | $30M | - | Sequoia Capital |
| Extension | 2024 | $300M debt | - | - |
| Series D | Oct 2025 | $300M | $5B | Paradigm, Sequoia |
| Latest | Nov 2025 | $1B | $11B | Paradigm, Sequoia, CapitalG |

**Total Raised**: ~$1.7 billion (equity + debt)

### Key Investors
- **Paradigm** (Lead)
- **Sequoia Capital**
- **CapitalG** (Alphabet's growth arm)
- **Andreessen Horowitz**
- **Coinbase Ventures**
- **Neo**
- **Anthos Capital**

## How Kalshi Works

### Regulatory Framework

```
┌─────────────────────────────────────────────────────────────┐
│                         CFTC                                 │
│           (Commodity Futures Trading Commission)             │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              DESIGNATED CONTRACT MARKET              │   │
│   │                      (DCM)                           │   │
│   │         Kalshi operates under this license           │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
│   Authority: Commodity Exchange Act (CEA)                    │
│   Product: "Event Contracts" (not gambling)                  │
└─────────────────────────────────────────────────────────────┘
```

### Trading Mechanics

1. **Account Creation**: KYC/AML verification required
2. **Funding**: Bank transfer, debit card, credit card
3. **Contract Selection**: Browse 3,500+ markets
4. **Order Placement**: Buy YES or NO contracts ($0.01-$0.99)
5. **Matching**: Exchange matches buyers and sellers
6. **Settlement**: Kalshi determines outcome (centralized)
7. **Payout**: Winners receive $1 per contract

### Fee Structure

| Contract Price | Fee per 100 Contracts |
|----------------|----------------------|
| Low price | $0.07 |
| High price | Up to $1.74 |
| Average | ~0.8% of contract value |
| Settlement fees | None |

**Fee Range**: 0.7-3.5% per trade

## Business Model & Financials

### Revenue Model
- **Transaction fees**: Maker-taker fee structure
- **No position-taking**: Pure exchange model (unlike sportsbooks)
- **B2C marketplace**: Two-sided prediction exchange

### Financial Performance
| Metric | Value | Period |
|--------|-------|--------|
| Revenue (H1 2025) | $200M+ | Profitable |
| Annualized Revenue Run Rate | $600-700M | Nov 2025 |
| Volume Growth | 6x | 6 months to Nov 2025 |

## Legal Victory: Election Contracts

### Background
- 2024: Kalshi sought to offer Congressional Control Contracts
- CFTC blocked under Regulation 40.11 (gaming prohibition)
- CFTC argued: election contracts = gambling = illegal

### Court Ruling (2024)
- **DC District Court**: Ruled in Kalshi's favor
- **Finding**: CFTC erred in categorizing as "gaming"
- **Result**: Vacated CFTC's decision
- **Appellate**: DC Circuit denied CFTC stay request

### Aftermath
- May 2025: CFTC dropped appeal (administration change)
- Election contracts now legal
- Expanded to sports, climate, crypto markets

## Market Categories

| Category | Example Contracts |
|----------|-------------------|
| **Politics** | Presidential elections, Senate control, Cabinet appointments |
| **Sports** | NFL games, championship outcomes, player props |
| **Economics** | CPI inflation, Fed rate decisions, GDP |
| **Finance** | Stock prices, company earnings, M&A |
| **Climate** | Temperature records, hurricane landfalls |
| **Crypto** | Bitcoin prices, ETF approvals |

## User Profile

**Typical Kalshi User**:
- Professional trader or retail investor
- Already trades stocks/options
- Values regulatory certainty
- Prefers bank account integration
- US-based

**Example Use Case**: Hedge S&P 500 portfolio by taking position on CPI inflation contract.

**Trading Behavior**:
- Open interest-to-volume ratio: 0.29 (lower than Polymarket)
- "Faster turnover" - more frequent trading
- Seeks hedging and macro exposure

## Distribution Partnerships

### Robinhood Integration
- Event contracts appear alongside equities, ETFs, options
- Same interface for traditional and prediction trading
- Lowers behavioral barrier for retail adoption

### DeFi Integration
- Partnerships with Pyth, Switchboard, Stork oracle networks
- Market data streamed on-chain for DeFi protocol integration

## Regulatory Challenges (2025)

### State Enforcement Actions

| State | Action | Status |
|-------|--------|--------|
| Nevada | Cease-and-desist (March 2025) | Kalshi suing |
| Massachusetts | AG lawsuit (Sept 2025) | Pending |
| Connecticut | Cease-and-desist (Dec 2025) | Kalshi suing |
| Maryland | Lawsuit | 38 states filed amicus brief |
| 7+ states total | Various C&D orders | Ongoing |

### Core Legal Issue
States argue: Sports event contracts = unlicensed sports betting
Kalshi argues: CFTC-regulated commodities preempt state gambling law

### Tribal Opposition
- Indian Gaming Association supporting state enforcement
- Wisconsin federal court case pending

**Legal Outlook**: Daniel Wallach (sports betting attorney) predicts Supreme Court case.

## Competitive Position

### Strengths
- **Only CFTC-regulated platform** (legitimacy)
- **US market access** (massive TAM)
- **Traditional finance rails** (bank integration)
- **Brokerage partnerships** (Robinhood distribution)
- **Profitable business model** (sustainable)
- **Institutional credibility** (Sequoia, CapitalG backing)

### Weaknesses
- **Centralized resolution** (trust required)
- **State legal exposure** (38 states opposing)
- **Limited market hours** (vs. 24/7 crypto)
- **KYC friction** (vs. Polymarket's pseudonymous access)
- **US-only** (geographic limitation)

## Kalshi vs Polymarket: Key Differences

| Dimension | Kalshi | Polymarket |
|-----------|--------|------------|
| **Regulation** | CFTC-regulated DCM | Decentralized, seeking approval |
| **Settlement** | USD | USDC (crypto) |
| **Resolution** | Centralized human adjudication | UMA oracle (decentralized) |
| **US Access** | Yes | Geo-blocked |
| **Fees** | 0.7-3.5% | None |
| **KYC** | Required | Wallet-based (pseudonymous) |
| **Volume (Q3 2025)** | $4.47B | $3.5B |
| **Position Duration** | Shorter (0.29 ratio) | Longer (0.38 ratio) |

## Market Share Dynamics

- **Pre-2024**: Near-zero volume for both platforms
- **2024**: Polymarket dominated (election coverage)
- **Q3 2025**: Kalshi overtook Polymarket (60% share)
- **Driving Factor**: US market access + brokerage integration
