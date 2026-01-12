# Polymarket Prediction Arbitrage Bot - Foundation Document

> **Purpose**: This document serves as a comprehensive foundation for building a prediction market arbitrage bot that monitors and executes trades on Polymarket's binary Up/Down markets. It contains all the technical details, API specifications, and strategic concepts needed to start from scratch.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [What We're Building](#2-what-were-building)
3. [Polymarket Platform Basics](#3-polymarket-platform-basics)
4. [API Reference](#4-api-reference)
5. [Trading Strategy Deep Dive](#5-trading-strategy-deep-dive)
6. [Data Models](#6-data-models)
7. [System Architecture](#7-system-architecture)
8. [Implementation Guide](#8-implementation-guide)

---

## 1. Project Overview

### The Opportunity

Polymarket offers binary prediction markets where users bet on outcomes like "Will BTC price go up in the next 15 minutes?". Each market has two outcomes (Up/Down), and when the market resolves, the winning outcome pays $1.00 per share while the losing outcome pays $0.00.

**The arbitrage opportunity**: If you can buy both outcomes for less than $1.00 combined, you're guaranteed a profit regardless of which outcome wins.

### Example

```
Market: "Bitcoin Up or Down" (15-minute market)

Current Prices:
  UP outcome:   $0.52 (ask price)
  DOWN outcome: $0.47 (ask price)
  Combined:     $0.99

If you buy 100 shares of EACH:
  Cost: (100 × $0.52) + (100 × $0.47) = $99.00

When market resolves:
  - If UP wins:   100 × $1.00 + 100 × $0.00 = $100.00
  - If DOWN wins: 100 × $0.00 + 100 × $1.00 = $100.00

Profit: $100.00 - $99.00 = $1.00 (guaranteed, regardless of outcome)
```

---

## 2. What We're Building

### Core Components

1. **Market Discovery** - Find active 15-minute BTC/ETH markets
2. **Price Monitoring** - Real-time orderbook data via WebSocket
3. **Trade Execution** - Place limit orders on both outcomes
4. **Position Tracking** - Track shares, costs, and P&L
5. **Risk Management** - Maintain balanced hedging
6. **Dashboard** - Real-time visualization of activity

### Target Markets

**15-Minute Binary Markets**:
- "Bitcoin Up or Down" (BTC)
- "Ethereum Up or Down" (ETH)

These markets have predictable slugs based on timestamps:
```
Pattern: {asset}-updown-15m-{unix_timestamp}

Examples:
- btc-updown-15m-1705000000
- eth-updown-15m-1705000900
```

New markets open every 15 minutes, providing continuous trading opportunities.

---

## 3. Polymarket Platform Basics

### Market Structure

Each market consists of:
- **Slug**: Unique identifier (e.g., `btc-updown-15m-1705000000`)
- **Condition ID**: On-chain identifier for the market
- **Token IDs**: Two ERC-1155 tokens representing each outcome
- **Outcomes**: Array like `["Up", "Down"]`
- **End Date**: When the market resolves

### Outcome Tokens

Each outcome is a tradeable token:
- **UP token**: Pays $1.00 if price goes up, $0.00 otherwise
- **DOWN token**: Pays $1.00 if price goes down, $0.00 otherwise

Tokens trade between $0.00 and $1.00, representing the market's probability assessment.

### Order Book (CLOB)

Polymarket uses a Central Limit Order Book:
- **Bids**: Buy orders at various prices
- **Asks**: Sell orders at various prices
- **Spread**: Difference between best bid and best ask
- **Midpoint**: Average of best bid and best ask

### Roles

- **Maker**: Posts limit orders, waits for fills (better prices, may not fill)
- **Taker**: Takes existing orders (immediate execution, pays spread)

---

## 4. API Reference

### 4.1 Gamma API (Market Metadata)

**Base URL**: `https://gamma-api.polymarket.com`

**Purpose**: Discover markets, get metadata, check resolution status

#### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/markets` | GET | List markets with optional filters |
| `/markets/{id}` | GET | Get specific market details |

#### Query Parameters for `/markets`

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Filter by market slug |
| `condition_id` | string | Filter by condition ID |
| `clob_token_ids` | string | Filter by token IDs |
| `closed` | boolean | Filter by resolution status |

#### Response Structure

```json
{
  "id": "123",
  "slug": "btc-updown-15m-1705000000",
  "question": "Bitcoin Up or Down",
  "description": "Will BTC price be higher or lower...",
  "outcomes": ["Up", "Down"],
  "outcomePrices": ["0.52", "0.48"],
  "clobTokenIds": ["token_id_up", "token_id_down"],
  "conditionId": "0x...",
  "startDate": "2024-01-11T12:00:00Z",
  "endDate": "2024-01-11T12:15:00Z",
  "closed": false,
  "volume": "50000",
  "liquidity": "10000"
}
```

#### Example Request

```python
import requests

response = requests.get(
    "https://gamma-api.polymarket.com/markets",
    params={"slug": "btc-updown-15m-1705000000"}
)
market = response.json()[0]  # Returns array
```

---

### 4.2 CLOB API (Trading & Orderbook)

**Base URL**: `https://clob.polymarket.com`

**Purpose**: Get live orderbook data, place/cancel orders

#### Public Endpoints (No Auth)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/book` | GET | Get orderbook for a token |
| `/markets` | GET | List all active CLOB markets |
| `/prices` | GET | Current prices |
| `/trades` | GET | Recent trades |

#### Orderbook Request

```python
response = requests.get(
    "https://clob.polymarket.com/book",
    params={"token_id": "your_token_id"}
)
```

#### Orderbook Response

```json
{
  "market": "token_id",
  "asset_id": "token_id",
  "bids": [
    {"price": "0.50", "size": "1000"},
    {"price": "0.49", "size": "500"}
  ],
  "asks": [
    {"price": "0.52", "size": "800"},
    {"price": "0.53", "size": "1200"}
  ],
  "hash": "0x..."
}
```

#### Authenticated Endpoints (Requires API Key)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orders` | POST | Create new order |
| `/orders` | GET | List your orders |
| `/orders/{id}` | DELETE | Cancel order |
| `/positions` | GET | Your positions |

#### Authentication

HMAC-SHA256 signature required:

```
Headers:
  POLY_API_KEY: your-api-key
  POLY_SIGNATURE: HMAC-SHA256(request_body, api_secret)
  POLY_TIMESTAMP: unix_timestamp
  POLY_PASSPHRASE: your-passphrase (optional)
```

#### Python SDK

```python
from py_clob_client.client import ClobClient

client = ClobClient(
    host="https://clob.polymarket.com",
    key="your-api-key",
    secret="your-secret",
    passphrase="your-passphrase",
    chain_id=137  # Polygon mainnet
)

# Get orderbook
book = client.get_order_book("token_id")

# Place order
order = client.create_and_post_order(
    token_id="token_id",
    price=0.50,
    size=100,
    side="BUY"
)
```

---

### 4.3 Data API (Trade History)

**Base URL**: `https://data-api.polymarket.com`

**Purpose**: Fetch historical trades for wallets

#### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/trades` | GET | Get trades for a wallet/market |

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user` | address | Wallet address to query |
| `limit` | int | Max results (up to 500) |
| `offset` | int | Pagination offset |
| `conditionId` | string | Filter by market |
| `side` | string | "BUY" or "SELL" |

#### Response Structure

```json
[
  {
    "transactionHash": "0x...",
    "timestamp": "2024-01-11T12:05:00Z",
    "slug": "btc-updown-15m-1705000000",
    "title": "Bitcoin Up or Down",
    "side": "BUY",
    "outcome": "Up",
    "size": "100.5",
    "price": "0.52",
    "asset": "token_id_up",
    "maker": false
  }
]
```

#### Example Request

```python
response = requests.get(
    "https://data-api.polymarket.com/trades",
    params={
        "user": "0x6031b6eed...",
        "limit": 500,
        "offset": 0
    }
)
trades = response.json()
```

---

### 4.4 WebSocket (Real-Time Prices)

**URL**: `wss://ws-subscriptions-clob.polymarket.com/ws/market`

**Purpose**: Real-time price updates, orderbook changes

#### Connection

```python
import websockets
import json

async def connect():
    uri = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    async with websockets.connect(uri) as ws:
        # Subscribe to assets
        await ws.send(json.dumps({
            "type": "market",
            "assets_ids": ["token_id_up", "token_id_down"]
        }))

        async for message in ws:
            data = json.loads(message)
            handle_message(data)
```

#### Message Types

**Price Change**:
```json
{
  "event_type": "price_change",
  "price_changes": [
    {
      "asset_id": "token_id",
      "price": "0.52",
      "best_bid": "0.51",
      "best_ask": "0.53",
      "timestamp": 1705000000000
    }
  ]
}
```

**Last Trade Price**:
```json
{
  "event_type": "last_trade_price",
  "asset_id": "token_id",
  "price": "0.52",
  "timestamp": 1705000000000
}
```

**Book Update**:
```json
{
  "event_type": "book",
  "asset_id": "token_id",
  "bids": [...],
  "asks": [...]
}
```

---

### 4.5 Goldsky Subgraph (On-Chain Data)

**URL**: `https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn`

**Purpose**: 100% accurate on-chain trade data via GraphQL

#### Example Query

```graphql
query GetTrades($wallet: String!, $tokens: [String!]!) {
  orderFilledEvents(
    where: {
      maker: $wallet
      makerAssetId_in: $tokens
    }
    orderBy: timestamp
    orderDirection: desc
    first: 1000
  ) {
    id
    transactionHash
    timestamp
    maker
    taker
    makerAssetId
    takerAssetId
    makerAmountFilled
    takerAmountFilled
  }
}
```

---

### 4.6 Smart Contracts

| Contract | Address | Purpose |
|----------|---------|---------|
| CTF Exchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` | Binary markets |
| NegRisk Exchange | `0xC5d563A36AE78145C45a50134d48A1215220f80a` | Multi-outcome |
| Conditional Tokens | ERC-1155 standard | Outcome tokens |

**Chain**: Polygon (chain_id: 137)

---

## 5. Trading Strategy Deep Dive

### 5.1 The Complete Set Arbitrage

**Core Concept**: Buy both outcomes for less than $1.00 total.

```
Combined Price = UP ask + DOWN ask

If Combined < $1.00:
    Edge = $1.00 - Combined
    Guaranteed profit = Edge × shares
```

**Example**:
```
UP ask: $0.51
DOWN ask: $0.48
Combined: $0.99

Buy 1000 shares of each:
  Cost: 1000 × $0.99 = $990
  Payout: 1000 × $1.00 = $1,000
  Profit: $10 (1% edge)
```

### 5.2 Key Metrics

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Combined Price** | up_price + down_price | Cost per complete set |
| **Edge** | 1.0 - combined_price | Profit per complete set |
| **Complete Sets** | min(up_shares, down_shares) | Fully hedged position |
| **Unhedged** | abs(up_shares - down_shares) | Directional exposure |
| **Hedge Ratio** | min(up,down) / max(up,down) | % of position hedged |

### 5.3 Position States

```python
# Perfect hedge (no directional risk)
up_shares = 100, down_shares = 100
complete_sets = 100
hedge_ratio = 1.0

# Partial hedge
up_shares = 100, down_shares = 80
complete_sets = 80
unhedged_up = 20  # Directional bet on UP
hedge_ratio = 0.8

# No hedge (pure directional)
up_shares = 100, down_shares = 0
complete_sets = 0
unhedged_up = 100
hedge_ratio = 0.0
```

### 5.4 P&L Calculation

```python
def calculate_pnl(position, winning_outcome):
    # Payout from winning shares
    if winning_outcome == "Up":
        payout = position.up_shares * 1.00
    else:
        payout = position.down_shares * 1.00

    # Total P&L
    total_revenue = payout + position.sell_revenue
    pnl = total_revenue - position.total_cost

    return pnl
```

### 5.5 Strategy Types

| Strategy | Hedge Ratio | Edge | Description |
|----------|-------------|------|-------------|
| **Arbitrage** | > 90% | > 0 | Buy both sides < $1.00 |
| **Market Making** | 70-90% | Variable | Capture bid-ask spread |
| **Directional** | < 30% | N/A | Bet on outcome |
| **Mixed** | 30-70% | Variable | Combination |

### 5.6 Risk Factors

1. **Inventory Imbalance**: Fills happen asynchronously; may end up with unhedged exposure
2. **Price Movement**: Market can move against unbalanced position
3. **Execution Risk**: Orders may not fill at expected prices
4. **Latency**: Slower execution = worse fills

### 5.7 Maker vs Taker

| Role | Pros | Cons |
|------|------|------|
| **Maker** | Better prices, earns rebate | May not fill |
| **Taker** | Immediate execution | Pays spread |

**Optimal Strategy**: Primarily maker (80%+) with taker for rebalancing.

---

## 6. Data Models

### 6.1 Trade Event

```python
@dataclass
class TradeEvent:
    id: str                    # Unique: tx_hash:asset_id
    tx_hash: str               # Blockchain transaction hash
    timestamp: int             # Unix timestamp
    wallet: str                # Wallet address
    wallet_name: str           # Human-readable name
    role: str                  # "maker" or "taker"
    side: str                  # "BUY" or "SELL"
    outcome: str               # "Up" or "Down"
    shares: float              # Number of shares
    usdc: float                # USDC amount
    price: float               # Price per share
    fee: float                 # Transaction fee
    market_slug: str           # Market identifier
    market_question: str       # Market question text
```

### 6.2 Wallet Position

```python
@dataclass
class WalletPosition:
    wallet: str
    wallet_name: str
    market_slug: str

    # Share holdings
    up_shares: float
    down_shares: float

    # Cost basis
    up_cost: float             # Total spent on UP
    down_cost: float           # Total spent on DOWN

    # Revenue from sells
    up_revenue: float
    down_revenue: float

    # Derived metrics
    complete_sets: float       # min(up, down)
    unhedged_up: float         # max(0, up - down)
    unhedged_down: float       # max(0, down - up)

    # Averages
    avg_up_price: float        # up_cost / up_shares
    avg_down_price: float      # down_cost / down_shares
    combined_price: float      # avg_up + avg_down

    # Strategy metrics
    edge: float                # 1.0 - combined_price
    hedge_ratio: float         # min(up,down) / max(up,down)

    # Trade counts
    total_trades: int
    buy_trades: int
    sell_trades: int
    maker_trades: int
    taker_trades: int
```

### 6.3 Market Context

```python
@dataclass
class MarketContext:
    slug: str                  # e.g., "btc-updown-15m-1705000000"
    question: str              # Market question
    condition_id: str          # On-chain identifier
    token_ids: Dict[str, str]  # {"up": "...", "down": "..."}
    outcomes: List[str]        # ["Up", "Down"]
    start_date: datetime
    end_date: datetime
    resolved: bool
    winning_outcome: str       # "Up", "Down", or None

    # Live orderbook data
    up_best_bid: float
    up_best_ask: float
    down_best_bid: float
    down_best_ask: float
    combined_bid: float        # up_bid + down_bid
    spread: float              # 1.0 - combined_bid
```

### 6.4 Price Point

```python
@dataclass
class PricePoint:
    timestamp: int
    timestamp_iso: str
    market_slug: str
    outcome: str               # "Up" or "Down"
    price: float               # Mid price
    best_bid: float
    best_ask: float
```

---

## 7. System Architecture

### 7.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    POLYMARKET APIS                          │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│ Gamma API   │ CLOB API    │ Data API    │ WebSocket       │
│ (metadata)  │ (orderbook) │ (trades)    │ (real-time)     │
└─────────────┴─────────────┴─────────────┴─────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND SERVICES                         │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│ Market      │ Trade       │ Price       │ Position        │
│ Discovery   │ Poller      │ Stream      │ Tracker         │
└─────────────┴─────────────┴─────────────┴─────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                               │
├─────────────────────────────────────────────────────────────┤
│                    SQLite Database                          │
│  ┌─────────┬──────────┬─────────┬────────┬───────────┐    │
│  │ trades  │ positions│ markets │ prices │ sessions  │    │
│  └─────────┴──────────┴─────────┴────────┴───────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER                                │
├─────────────────────────────────────────────────────────────┤
│              FastAPI (REST + WebSocket)                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND                                 │
├─────────────────────────────────────────────────────────────┤
│              React Dashboard (TypeScript)                   │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Service Responsibilities

**Market Discovery**
- Generate potential market slugs based on timestamps
- Query Gamma API to find active markets
- Track market lifecycle (active → resolved)

**Trade Poller**
- Poll Data API for wallet trades every 2 seconds
- Deduplicate trades by ID
- Emit new trades to position tracker

**Price Stream**
- Maintain WebSocket connection
- Subscribe to active market token IDs
- Save price snapshots to database
- Emit price updates to dashboard

**Position Tracker**
- Process incoming trades
- Update position metrics
- Calculate derived values (edge, hedge ratio)

### 7.3 Database Schema

```sql
-- Trades table
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    tx_hash TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    wallet TEXT NOT NULL,
    wallet_name TEXT,
    role TEXT NOT NULL,
    side TEXT NOT NULL,
    outcome TEXT NOT NULL,
    shares REAL NOT NULL,
    usdc REAL NOT NULL,
    price REAL NOT NULL,
    fee REAL DEFAULT 0,
    market_slug TEXT NOT NULL,
    market_question TEXT,
    session_id TEXT,
    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Positions table
CREATE TABLE positions (
    wallet TEXT NOT NULL,
    market_slug TEXT NOT NULL,
    wallet_name TEXT,
    up_shares REAL DEFAULT 0,
    down_shares REAL DEFAULT 0,
    up_cost REAL DEFAULT 0,
    down_cost REAL DEFAULT 0,
    up_revenue REAL DEFAULT 0,
    down_revenue REAL DEFAULT 0,
    complete_sets REAL DEFAULT 0,
    unhedged_up REAL DEFAULT 0,
    unhedged_down REAL DEFAULT 0,
    avg_up_price REAL DEFAULT 0,
    avg_down_price REAL DEFAULT 0,
    combined_price REAL DEFAULT 0,
    edge REAL DEFAULT 0,
    hedge_ratio REAL DEFAULT 1,
    total_trades INTEGER DEFAULT 0,
    buy_trades INTEGER DEFAULT 0,
    sell_trades INTEGER DEFAULT 0,
    maker_trades INTEGER DEFAULT 0,
    taker_trades INTEGER DEFAULT 0,
    first_trade_ts INTEGER,
    last_trade_ts INTEGER,
    PRIMARY KEY (wallet, market_slug)
);

-- Markets table
CREATE TABLE markets (
    slug TEXT PRIMARY KEY,
    condition_id TEXT,
    question TEXT,
    token_ids TEXT,  -- JSON: {"up": "...", "down": "..."}
    outcomes TEXT,   -- JSON: ["Up", "Down"]
    start_date TEXT,
    end_date TEXT,
    resolved INTEGER DEFAULT 0,
    winning_outcome TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Prices table
CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    timestamp_iso TEXT,
    market_slug TEXT NOT NULL,
    outcome TEXT NOT NULL,
    price REAL,
    best_bid REAL,
    best_ask REAL,
    session_id TEXT
);

-- Indexes
CREATE INDEX idx_trades_wallet ON trades(wallet);
CREATE INDEX idx_trades_market ON trades(market_slug);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_prices_market ON prices(market_slug);
CREATE INDEX idx_prices_timestamp ON prices(timestamp);
```

### 7.4 Tech Stack

**Backend**:
- Python 3.8+
- FastAPI (REST API + WebSocket server)
- SQLite (WAL mode for concurrent access)
- aiohttp (async HTTP client)
- websockets (WebSocket client)
- Pydantic (data validation)

**Frontend**:
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Recharts (data visualization)

---

## 8. Implementation Guide

### 8.1 Project Structure

```
prediction-arbitrage/
├── backend/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration
│   ├── models.py            # Pydantic models
│   ├── database.py          # SQLite operations
│   ├── api.py               # FastAPI routes
│   ├── services/
│   │   ├── discovery.py     # Market discovery
│   │   ├── trade_poller.py  # Trade fetching
│   │   ├── price_stream.py  # WebSocket prices
│   │   └── position.py      # Position tracking
│   └── utils/
│       └── logger.py        # Logging setup
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── context/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
│
├── data/
│   └── tracker.db
│
├── requirements.txt
└── README.md
```

### 8.2 Configuration

```python
# config.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class Config:
    # Target wallets to monitor
    TARGET_WALLETS: Dict[str, str] = {
        "0x6031b6eed...": "gabagool22",
    }

    # Market filter
    MARKET_PATTERN: str = r"(btc|eth)-updown-15m-\d+"

    # API URLs
    GAMMA_API: str = "https://gamma-api.polymarket.com"
    CLOB_API: str = "https://clob.polymarket.com"
    DATA_API: str = "https://data-api.polymarket.com"
    WS_URL: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    # Polling intervals
    TRADE_POLL_INTERVAL: float = 2.0      # seconds
    MARKET_POLL_INTERVAL: float = 30.0    # seconds
    PRICE_SAVE_INTERVAL: float = 1.0      # seconds

    # Server
    HTTP_PORT: int = 8000

    # Database
    DATABASE_PATH: str = "data/tracker.db"
```

### 8.3 Key Implementation Steps

1. **Set up database**
   - Create SQLite database with schema
   - Implement CRUD operations

2. **Implement market discovery**
   - Generate slug patterns for current time
   - Query Gamma API for market details
   - Store active markets

3. **Implement trade poller**
   - Poll Data API for target wallet trades
   - Deduplicate by trade ID
   - Process new trades

4. **Implement price stream**
   - Connect to WebSocket
   - Subscribe to active market tokens
   - Save price points

5. **Implement position tracking**
   - Calculate running totals on each trade
   - Compute derived metrics

6. **Build API layer**
   - REST endpoints for data retrieval
   - WebSocket for real-time updates

7. **Build dashboard**
   - Connect to WebSocket
   - Display trades, positions, prices
   - Visualize with charts

### 8.4 Polling Recommendations

| Task | Interval | Notes |
|------|----------|-------|
| Trade polling | 2 seconds | Catch trades quickly |
| Market discovery | 30 seconds | New markets every 15 min |
| Price saves | 1 second | Throttle WebSocket saves |
| Position resolution | After market closes + 2 min | Wait for final trades |

### 8.5 Error Handling

- Implement retry logic with exponential backoff
- Handle WebSocket disconnections with auto-reconnect
- Log all API errors with context
- Graceful degradation when APIs are unavailable

---

## Summary

This document provides everything needed to build a Polymarket prediction arbitrage system:

1. **APIs**: Full reference for Gamma, CLOB, Data, and WebSocket APIs
2. **Strategy**: Complete explanation of arbitrage mechanics
3. **Models**: Data structures for trades, positions, markets
4. **Architecture**: System design and component interactions
5. **Implementation**: Step-by-step guide to build the system

The core arbitrage opportunity is simple: buy both outcomes for less than $1.00 combined to guarantee profit. The complexity lies in execution - managing inventory, handling asynchronous fills, and maintaining balanced hedges.

---

*Document Version: 1.0*
*Last Updated: January 2026*
