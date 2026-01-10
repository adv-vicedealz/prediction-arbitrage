# Prediction Markets: Data Sources & Tools for Bot Building

## Data Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              PREDICTION MARKET DATA STACK                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   LAYER 1: RAW ON-CHAIN DATA                                │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Polygon RPC → OrderFilled events, token transfers  │   │
│   │  Contract state → positions, balances               │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│   LAYER 2: INDEXED DATA                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Dune Analytics → SQL-queryable historical data     │   │
│   │  Goldsky → Real-time indexing                       │   │
│   │  The Graph → Subgraph queries                       │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│   LAYER 3: PLATFORM APIs                                     │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  CLOB API → Order book, trades, positions           │   │
│   │  Gamma API → Market metadata, resolution info       │   │
│   │  Kalshi API → Markets, orders, portfolio            │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│   LAYER 4: ANALYTICS PLATFORMS                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  PolymarketAnalytics → Dashboards, leaderboards     │   │
│   │  PolyTrack → Whale tracking, alerts                 │   │
│   │  Custom dashboards → Dune, Flipside                 │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Polymarket APIs

### 1. CLOB API (Trading)

**Base URL**: `https://clob.polymarket.com`

**Purpose**: Order management, trading, real-time order book

#### Key Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/markets` | GET | No | List all markets |
| `/markets/{id}` | GET | No | Market details |
| `/book` | GET | No | Order book snapshot |
| `/midpoint` | GET | No | Current midpoint price |
| `/spread` | GET | No | Bid-ask spread |
| `/price` | GET | No | Current price |
| `/prices-history` | GET | No | Historical prices |
| `/trades` | GET | No | Recent trades |
| `/order` | POST | Yes | Create order |
| `/orders` | GET | Yes | Your open orders |
| `/order/{id}` | DELETE | Yes | Cancel order |
| `/positions` | GET | Yes | Your positions |

#### Authentication

```python
# Headers required for authenticated endpoints
headers = {
    "POLY_API_KEY": "your-api-key",
    "POLY_SIGNATURE": "hmac-sha256-signature",
    "POLY_TIMESTAMP": "unix-timestamp",  # 30-second expiry
    "POLY_PASSPHRASE": "optional"
}
```

#### Order Book Response

```json
{
  "market": "0x...",
  "asset_id": "token_id",
  "hash": "orderbook_hash",
  "bids": [
    {"price": "0.55", "size": "1000"},
    {"price": "0.54", "size": "2500"}
  ],
  "asks": [
    {"price": "0.57", "size": "800"},
    {"price": "0.58", "size": "1200"}
  ],
  "timestamp": "1704067200"
}
```

### 2. Gamma API (Metadata)

**Base URL**: `https://gamma-api.polymarket.com`

**Purpose**: Market metadata, resolution info, event details

**Authentication**: Not required (read-only)

#### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/markets` | All markets with metadata |
| `/markets?id={id}` | Single market |
| `/markets?slug={slug}` | By URL slug |
| `/markets?active=true` | Active only |
| `/events` | Event groupings |
| `/tags` | Market categories |

#### Market Object Structure

```json
{
  "id": "market_id",
  "question": "Will X happen?",
  "conditionId": "0x...",
  "slug": "will-x-happen",
  "resolutionSource": "https://source.com",
  "endDate": "2025-12-31T23:59:59Z",
  "category": "Politics",
  "liquidity": "250000",
  "volume": "1500000",
  "outcomes": ["Yes", "No"],
  "outcomePrices": ["0.65", "0.35"],
  "clob_token_ids": ["token_yes", "token_no"],
  "marketMakerAddress": "0x...",
  "active": true,
  "closed": false
}
```

#### Key Identifiers

| ID Type | Description | Example |
|---------|-------------|---------|
| `id` | Gamma market ID | `"abc123"` |
| `conditionId` | On-chain condition | `"0x9915bea..."` |
| `clob_token_ids` | Trading tokens [YES, NO] | `["123...", "456..."]` |
| `slug` | URL-friendly name | `"trump-wins-2024"` |

### 3. WebSocket Streams

**URL**: `wss://ws-subscriptions-clob.polymarket.com/ws/market`

```python
import websockets
import json

async def subscribe_orderbook(token_id):
    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({
            "type": "subscribe",
            "channel": "book",
            "assets_id": token_id
        }))

        async for msg in ws:
            data = json.loads(msg)
            print(f"Update: {data}")
```

---

## Kalshi API

**Base URL**: `https://api.elections.kalshi.com/trade-api/v2`

### Authentication

```python
# RSA-PSS signature authentication
from kalshi_python import Configuration, KalshiClient

config = Configuration(
    host="https://api.elections.kalshi.com/trade-api/v2"
)

# Load private key
with open("private_key.pem", "r") as f:
    config.private_key_pem = f.read()

config.api_key_id = "your-api-key-id"
client = KalshiClient(config)
```

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/markets` | GET | List markets |
| `/markets/{ticker}` | GET | Market details |
| `/markets/{ticker}/orderbook` | GET | Order book |
| `/events` | GET | Event groupings |
| `/portfolio/orders` | GET | Your orders |
| `/portfolio/orders` | POST | Place order |
| `/portfolio/positions` | GET | Your positions |
| `/portfolio/balance` | GET | Account balance |

### WebSocket

```python
# Real-time data streaming
# First authenticate via REST, then connect with token
ws_url = "wss://trading-api.kalshi.com/trade-api/ws/v2"
```

### Rate Limits

| Tier | Limit | Use Case |
|------|-------|----------|
| Standard | 10 req/sec | Individual traders |
| Pro | 100 req/sec | Active traders |
| Institutional | Custom | HFT/Market makers |

---

## Dune Analytics

### Available Dashboards

| Dashboard | Creator | URL | Focus |
|-----------|---------|-----|-------|
| Polymarket | rchen8 | dune.com/rchen8/polymarket | General metrics |
| Activity & Volume | filarm | dune.com/filarm/polymarket-activity | Volume trends |
| CLOB Stats | lifewillbeokay | dune.com/lifewillbeokay/polymarket-clob-stats | Order book |
| Market Analyzer | lifewillbeokay | dune.com/lifewillbeokay/polymarket-market-analyzer | Per-market |
| Polygon Overview | petertherock | dune.com/petertherock/polymarket-on-polygon | Chain data |

### Useful SQL Queries

#### Daily Volume

```sql
SELECT
    date_trunc('day', block_time) AS day,
    SUM(amount_usd) AS daily_volume,
    COUNT(*) AS trade_count,
    COUNT(DISTINCT trader) AS unique_traders
FROM polymarket.trades
WHERE block_time > now() - interval '30 days'
GROUP BY 1
ORDER BY 1 DESC
```

#### Whale Activity

```sql
SELECT
    trader,
    SUM(amount_usd) AS total_volume,
    COUNT(*) AS trade_count,
    AVG(amount_usd) AS avg_trade_size
FROM polymarket.trades
WHERE block_time > now() - interval '7 days'
GROUP BY 1
HAVING SUM(amount_usd) > 50000
ORDER BY 2 DESC
LIMIT 100
```

#### Market Performance

```sql
SELECT
    market_id,
    SUM(CASE WHEN side = 'buy' THEN amount_usd ELSE 0 END) AS buy_volume,
    SUM(CASE WHEN side = 'sell' THEN amount_usd ELSE 0 END) AS sell_volume,
    COUNT(DISTINCT trader) AS participants
FROM polymarket.trades
WHERE block_time > now() - interval '24 hours'
GROUP BY 1
ORDER BY (buy_volume + sell_volume) DESC
```

### LiveFetch for Real-Time Data

```sql
-- Fetch live market data from Gamma API
SELECT * FROM livefetch(
    'https://gamma-api.polymarket.com/markets?active=true',
    json_format='lines'
)
```

---

## Python SDKs

### py-clob-client (Official Polymarket)

```bash
pip install py-clob-client
```

#### Complete Setup

```python
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
import os

# Configuration
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon mainnet

# Read-only client (no auth)
public_client = ClobClient(HOST, CHAIN_ID)

# Get markets
markets = public_client.get_markets()

# Get order book
book = public_client.get_order_book(token_id="...")

# Get midpoint
mid = public_client.get_midpoint(token_id="...")
```

#### Authenticated Trading

```python
from py_clob_client.client import ClobClient
from py_clob_client.order_builder.constants import BUY, SELL
from eth_account import Account

# Create wallet from private key
private_key = os.environ["PRIVATE_KEY"]
account = Account.from_key(private_key)

# Initialize client
client = ClobClient(
    host=HOST,
    chain_id=CHAIN_ID,
    key=private_key
)

# Generate API credentials (first time only)
creds = client.create_api_creds()
print(f"Save these: {creds}")

# Re-initialize with credentials
client = ClobClient(
    host=HOST,
    chain_id=CHAIN_ID,
    key=private_key,
    creds=ApiCreds(
        api_key=creds.api_key,
        api_secret=creds.api_secret,
        api_passphrase=creds.api_passphrase
    ),
    signature_type=0  # EOA wallet
)

# Create order
order = client.create_order(
    token_id="your_token_id",
    price=0.55,
    size=100,
    side=BUY
)

# Submit order
response = client.post_order(order)
print(f"Order ID: {response['orderID']}")

# Check positions
positions = client.get_positions()

# Cancel order
client.cancel_order(order_id="...")
```

### kalshi-python (Official Kalshi)

```bash
pip install kalshi-python
```

```python
from kalshi_python import Configuration, KalshiClient

config = Configuration()
config.host = "https://api.elections.kalshi.com/trade-api/v2"

# Load RSA private key
with open("kalshi_private_key.pem") as f:
    config.private_key_pem = f.read()
config.api_key_id = "your-key-id"

client = KalshiClient(config)

# Get markets
markets = client.get_markets()

# Get specific market
market = client.get_market(ticker="PRES-2024")

# Place order
order = client.create_order(
    ticker="PRES-2024",
    side="yes",
    type="limit",
    count=10,
    price=55  # in cents
)
```

### polymarket-apis (Community)

```bash
pip install polymarket-apis
```

```python
from polymarket_apis import PolymarketAPI

api = PolymarketAPI()

# Get all markets
markets = api.get_markets()

# Filter active markets
active = api.get_markets(active=True)

# Get by condition
market = api.get_market_by_condition("0x...")
```

---

## Analytics Platforms

### PolymarketAnalytics.com

**Features**:
- Trader leaderboards (updated every 5 minutes)
- Market comparison (Polymarket vs Kalshi)
- Arbitrage opportunity finder
- Historical price charts
- Powered by Goldsky infrastructure

**API Access**: Contact for institutional data feeds

### PolyTrack (polytrackhq.app)

**Features**:
- Whale wallet tracking
- Real-time trade alerts
- Cluster detection (related wallets)
- Portfolio analytics
- Copy trading signals

**Subscription**: Freemium model

### Parsec

**Features**:
- Real-time order flow
- Live trades visualization
- Top holders analysis
- Open interest tracking
- Multi-outcome market views

---

## On-Chain Data Sources

### Direct RPC Access

```python
from web3 import Web3

# Polygon RPC endpoints
POLYGON_RPC = "https://polygon-rpc.com"
# Or use Alchemy/Infura for reliability:
# "https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY"

w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

# CTF Exchange contract
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

# Monitor OrderFilled events
contract = w3.eth.contract(address=CTF_EXCHANGE, abi=CTF_ABI)

# Get recent events
events = contract.events.OrderFilled.get_logs(
    fromBlock=w3.eth.block_number - 1000
)
```

### Key Contract Addresses (Polygon)

| Contract | Address |
|----------|---------|
| CTF Exchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` |
| NegRisk CTF Exchange | `0xC5d563A36AE78145C45a50134d48A1215220f80a` |
| USDC (Polygon) | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` |
| Conditional Tokens | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` |

### PolygonScan

- Explorer: `polygonscan.com`
- API: `api.polygonscan.com`
- Use for transaction lookup, contract verification

---

## External Data for Trading

### Price Feeds (for crypto markets)

| Source | Use Case | Endpoint |
|--------|----------|----------|
| Binance | BTC/ETH spot | `api.binance.com/api/v3/ticker/price` |
| Coinbase | USD prices | `api.coinbase.com/v2/prices` |
| CoinGecko | Multi-asset | `api.coingecko.com/api/v3` |

### News & Sentiment

| Source | Type | Access |
|--------|------|--------|
| Twitter/X API | Social sentiment | API subscription |
| NewsAPI | Headlines | Free tier available |
| Reddit API | Community sentiment | Free |
| Polymarket's X feed | Platform-specific | Public |

---

## Data Pipeline Architecture

### For Trading Bot

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA PIPELINE                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   INGEST                                                     │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │ CLOB WS     │  │ Gamma REST  │  │ External    │        │
│   │ (real-time) │  │ (metadata)  │  │ (prices)    │        │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│          │                │                │                │
│          └────────────────┼────────────────┘                │
│                           │                                  │
│   NORMALIZE               ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Unified market model                                │   │
│   │  {market_id, yes_price, no_price, volume, ...}      │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│   STORE                   ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  TimescaleDB / InfluxDB / Redis                     │   │
│   │  - Price history                                     │   │
│   │  - Order book snapshots                              │   │
│   │  - Trade log                                         │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│   ANALYZE                 ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Strategy engine consumes data                       │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Reference: Getting Started

### Minimum Viable Data Stack

1. **py-clob-client** - Trading & order book
2. **Gamma API** - Market metadata
3. **Dune** - Historical analysis
4. **PolyTrack** - Whale monitoring

### Environment Setup

```bash
# Install dependencies
pip install py-clob-client web3==6.14.0 python-dotenv requests

# .env file
PRIVATE_KEY=your_wallet_private_key
POLY_API_KEY=your_api_key
POLY_API_SECRET=your_api_secret
POLY_PASSPHRASE=optional
```

### First API Call

```python
import requests

# No auth needed
response = requests.get(
    "https://gamma-api.polymarket.com/markets",
    params={"active": "true", "limit": 10}
)

markets = response.json()
for m in markets:
    print(f"{m['question']}: {m['outcomePrices']}")
```
