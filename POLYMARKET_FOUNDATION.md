# Polymarket Prediction Arbitrage - Foundation Document

> **Purpose**: This document explains the Polymarket prediction market platform, the arbitrage opportunity, and all the technical information needed to analyze and eventually build trading systems.

---

## Goals

### Immediate Goal: Understand Profitable Traders

Before building a trading bot, we need to understand **how profitable traders operate**:
- Which wallets are consistently profitable?
- What strategies do they use?
- What's their trade timing and sizing?
- How do they manage risk and hedge positions?
- What edge do they capture and how?

This means building tools to **monitor, track, and analyze** successful traders on Polymarket.

### End Goal: Build a Trading Bot

Once we understand the winning strategies, the end goal is to build an **automated trading bot** that:
- Identifies arbitrage opportunities in real-time
- Executes trades automatically
- Manages risk through proper hedging
- Generates consistent profits

---

## Table of Contents

1. [The Opportunity](#1-the-opportunity)
2. [Polymarket Platform Basics](#2-polymarket-platform-basics)
3. [API Reference](#3-api-reference)
4. [Trading Strategy Concepts](#4-trading-strategy-concepts)

---

## 1. The Opportunity

### What is Polymarket?

Polymarket is a prediction market platform where users bet on real-world outcomes. Markets have binary outcomes (Yes/No, Up/Down), and when the market resolves, the winning outcome pays **$1.00 per share** while the losing outcome pays **$0.00**.

### The Arbitrage Opportunity

**If you can buy both outcomes for less than $1.00 combined, you're guaranteed a profit regardless of which outcome wins.**

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

### Target Markets

**15-Minute Binary Markets** (new market every 15 minutes):
- "Bitcoin Up or Down" (BTC)
- "Ethereum Up or Down" (ETH)

These markets have predictable slugs based on timestamps:
```
Pattern: {asset}-updown-15m-{unix_timestamp}

Examples:
- btc-updown-15m-1705000000
- eth-updown-15m-1705000900
```

---

## 2. Polymarket Platform Basics

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

## 3. API Reference

### 3.1 Gamma API (Market Metadata)

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

### 3.2 CLOB API (Trading & Orderbook)

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

### 3.3 Data API (Trade History)

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

### 3.4 WebSocket (Real-Time Prices)

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

### 3.5 Goldsky Subgraph (On-Chain Data)

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

### 3.6 Smart Contracts

| Contract | Address | Purpose |
|----------|---------|---------|
| CTF Exchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` | Binary markets |
| NegRisk Exchange | `0xC5d563A36AE78145C45a50134d48A1215220f80a` | Multi-outcome |
| Conditional Tokens | ERC-1155 standard | Outcome tokens |

**Chain**: Polygon (chain_id: 137)

---

## 4. Trading Strategy Concepts

### 4.1 The Complete Set Arbitrage

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

### 4.2 Key Metrics to Analyze

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Combined Price** | up_price + down_price | Cost per complete set |
| **Edge** | 1.0 - combined_price | Profit per complete set |
| **Complete Sets** | min(up_shares, down_shares) | Fully hedged position |
| **Unhedged** | abs(up_shares - down_shares) | Directional exposure |
| **Hedge Ratio** | min(up,down) / max(up,down) | % of position hedged |

### 4.3 Position States

```
Perfect hedge (no directional risk):
  up_shares = 100, down_shares = 100
  complete_sets = 100
  hedge_ratio = 1.0

Partial hedge:
  up_shares = 100, down_shares = 80
  complete_sets = 80
  unhedged_up = 20  (directional bet on UP)
  hedge_ratio = 0.8

No hedge (pure directional):
  up_shares = 100, down_shares = 0
  complete_sets = 0
  unhedged_up = 100
  hedge_ratio = 0.0
```

### 4.4 P&L Calculation

```
When market resolves:
  - Winning shares pay $1.00 each
  - Losing shares pay $0.00 each

P&L = (winning_shares × $1.00) + sell_revenue - total_cost
```

### 4.5 Strategy Types

| Strategy | Hedge Ratio | Edge | Description |
|----------|-------------|------|-------------|
| **Arbitrage** | > 90% | > 0 | Buy both sides < $1.00 |
| **Market Making** | 70-90% | Variable | Capture bid-ask spread |
| **Directional** | < 30% | N/A | Bet on outcome |
| **Mixed** | 30-70% | Variable | Combination |

### 4.6 Risk Factors

1. **Inventory Imbalance**: Fills happen asynchronously; may end up with unhedged exposure
2. **Price Movement**: Market can move against unbalanced position
3. **Execution Risk**: Orders may not fill at expected prices
4. **Latency**: Slower execution = worse fills

### 4.7 Maker vs Taker

| Role | Pros | Cons |
|------|------|------|
| **Maker** | Better prices, earns rebate | May not fill |
| **Taker** | Immediate execution | Pays spread |

**Optimal Strategy**: Primarily maker (80%+) with taker for rebalancing.

---

## Summary

**Immediate Goal**: Build tools to monitor and analyze profitable traders on Polymarket to understand their strategies, timing, sizing, and risk management.

**End Goal**: Use these insights to build an automated trading bot that captures arbitrage opportunities.

**The Core Opportunity**: Buy both outcomes for less than $1.00 combined to guarantee profit regardless of which outcome wins.

---

*Document Version: 1.1*
