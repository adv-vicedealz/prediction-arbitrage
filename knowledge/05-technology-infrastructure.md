# Prediction Markets: Technology & Infrastructure

## Blockchain Architecture

### Why Blockchain for Prediction Markets?

| Benefit | Description |
|---------|-------------|
| **Transparency** | All transactions publicly verifiable on-chain |
| **Immutability** | Cannot alter historical records |
| **Trustlessness** | No central authority required |
| **Automation** | Smart contracts execute settlements |
| **Censorship Resistance** | No single point of failure |
| **Global Access** | 24/7 operation, permissionless |

### Layer 2 Scaling: Why Polygon?

Polymarket chose Polygon (Ethereum L2) for:

| Factor | Ethereum L1 | Polygon L2 |
|--------|-------------|------------|
| Transaction Cost | $5-50+ | $0.001-0.01 |
| Settlement Time | 12-15 seconds | 2-3 seconds |
| Throughput | ~15 TPS | ~7,000 TPS |
| Security | Native | Inherits from Ethereum |

**Result**: Enables micro-transactions, frequent trading, and low-cost market operations.

---

## Smart Contract Architecture

### Polymarket Contract Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    POLYMARKET CONTRACTS                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              CTF EXCHANGE                            │    │
│  │  - Handles binary YES/NO markets                     │    │
│  │  - Matches maker and taker orders                    │    │
│  │  - Manages position tokens                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │          NEGRISK_CTF EXCHANGE                        │    │
│  │  - Handles multi-outcome markets                     │    │
│  │  - Complex conditional logic                         │    │
│  │  - NegRisk position management                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │          CTF / NEGRISK ADAPTER                       │    │
│  │  - Manages trader positions                          │    │
│  │  - Tracks balances and P&L                          │    │
│  │  - Handles token transfers                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Order Execution Flow

```
User Places Order
       │
       ▼
┌──────────────────┐
│  USDC Deposited  │ ◄── User's wallet (MetaMask, etc.)
│  to Smart Contract│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Order Matching  │ ◄── Each Polygon tx has 1 taker, 1+ makers
│     Engine       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Position Tokens  │ ◄── YES or NO tokens minted
│    Issued        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  On-Chain        │ ◄── Publicly verifiable
│  Recording       │
└──────────────────┘
```

### Transaction Template

Every Polymarket trade follows a rigid structure:
- Maximum one group of matched orders per Polygon transaction
- Each matched order set has exactly one taker
- Each matched order set has at least one maker
- All receipts stored on-chain

---

## Oracle Systems

### The Oracle Problem

**Challenge**: How do smart contracts know real-world outcomes?
- Blockchains are deterministic, isolated systems
- Cannot natively access external data
- Need trusted bridge between on-chain and off-chain

### UMA Protocol (Polymarket's Oracle)

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     UMA ORACLE SYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           OPTIMISTIC ORACLE V2 (OOV2)                 │   │
│  │                                                        │   │
│  │  Assumption: Data is accurate unless challenged       │   │
│  │                                                        │   │
│  │  1. Proposer submits answer + posts bond              │   │
│  │  2. Challenge window opens (2 hours for Polymarket)   │   │
│  │  3. If undisputed → outcome accepted                  │   │
│  │  4. If disputed → escalates to DVM                    │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼ (if disputed)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        DATA VERIFICATION MECHANISM (DVM)              │   │
│  │                                                        │   │
│  │  Commit-Reveal Voting Process:                        │   │
│  │  1. UMA tokenholders vote on correct answer           │   │
│  │  2. 48-96 hour voting period                          │   │
│  │  3. Honest voters earn rewards                        │   │
│  │  4. Incorrect/absent voters penalized                 │   │
│  │  5. Majority determines final outcome                 │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Key Statistics
- ~98.5% of requests resolved without dispute
- Economic incentives align honest behavior
- Bond requirement discourages frivolous proposals/disputes

#### Why Optimistic?
- Assumes data correct unless proven wrong
- Only invokes expensive DVM when needed
- Cost-efficient for routine resolutions
- Supports broad data types (not just price feeds)

### Polymarket Market Integrity Committee

For edge cases and ambiguous outcomes:
- Human adjudication layer
- Handles disputes UMA can't resolve cleanly
- Final authority on market resolution

### Kalshi's Oracle (Centralized)

| Aspect | UMA (Polymarket) | Kalshi |
|--------|------------------|--------|
| Resolution | Decentralized voting | Centralized determination |
| Speed | Hours (dispute period) | Immediate |
| Trust Model | Trustless (economic incentives) | Trust Kalshi |
| Appeal | DVM voting | Regulatory complaint |
| Transparency | On-chain | Internal |

---

## Settlement & Currency

### USDC (Polymarket)

| Property | Details |
|----------|---------|
| Type | Stablecoin (USD-pegged) |
| Issuer | Circle |
| Collateral | Fully backed by USD reserves |
| Blockchain | Polygon (for Polymarket) |
| Volatility | Minimal (~$1.00) |

**Advantages**:
- Reduces volatility risk during position holding
- Enables large orders without price impact
- Familiar dollar-denominated thinking
- Global accessibility (no bank required)

### USD (Kalshi)

Traditional rails:
- Bank account linking
- Debit/credit card
- Wire transfer
- Fully US-regulated

---

## API & Data Access

### Polymarket API

```
Available Endpoints:
├── Markets
│   ├── GET /markets - List all markets
│   ├── GET /markets/{id} - Market details
│   └── GET /markets/{id}/orderbook - Order book
├── Trading
│   ├── POST /orders - Place order
│   ├── DELETE /orders/{id} - Cancel order
│   └── GET /positions - User positions
└── Historical
    ├── GET /trades - Trade history
    └── GET /prices - Price history
```

### Data Products

| Provider | Data Type | Use Case |
|----------|-----------|----------|
| Polymarket | Real-time odds | News/research |
| ICE (via Polymarket) | Institutional data feeds | Trading desks |
| Kalshi | API access | DeFi integration |
| Pyth/Switchboard/Stork | On-chain feeds | Smart contract consumption |

---

## On-Chain Analytics

### Available Data

All Polymarket transactions are on-chain:
- Order placement
- Trade execution
- Position changes
- Settlement payouts

### Analysis Tools

| Tool | Description |
|------|-------------|
| Dune Analytics | SQL queries on blockchain data |
| Token Terminal | Trading metrics dashboard |
| Polymarket Analytics | Dedicated analytics platform |
| Custom indexers | Direct Polygon node queries |

### Research Applications

- Wash trading detection
- Whale activity monitoring
- Liquidity analysis
- Market manipulation identification
- Price discovery studies

---

## Technical Risks

### Oracle Manipulation
- UMA token governance attacks possible
- 2025: $2M whale loss from oracle issues
- Mitigation: Bond requirements, DVM security

### Smart Contract Vulnerabilities
- Immutable code once deployed
- Bugs can lead to fund loss
- Mitigation: Audits, bug bounties

### Network Congestion
- High activity can spike gas costs
- Polygon more resilient than Ethereum L1
- May impact execution during peak events

### Centralization Points
- Market Integrity Committee (Polymarket)
- UMA token holder concentration
- API infrastructure reliance

---

## Future Technology Trends

### Cross-Chain Expansion
- Markets on multiple blockchains
- Solana (Drift), other L2s
- Chain-agnostic liquidity

### DeFi Integration
- Prediction market positions as collateral
- Automated hedging strategies
- Yield farming with outcome tokens

### AI-Powered Forecasting
- AI agents as market participants
- Automated research and trading
- Metaculus experimenting with AI forecasters

### Privacy Enhancements
- Zero-knowledge proofs for private betting
- Selective disclosure of positions
- Regulatory-compliant privacy
