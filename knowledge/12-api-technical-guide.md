# Prediction Markets: API & Technical Guide

## Polymarket API Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  POLYMARKET ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                    ┌──────────────────┐                     │
│                    │   Frontend UI    │                     │
│                    │  (polymarket.com)│                     │
│                    └────────┬─────────┘                     │
│                             │                               │
│              ┌──────────────┼──────────────┐               │
│              │              │              │               │
│              ▼              ▼              ▼               │
│     ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│     │  CLOB API  │  │ Gamma API  │  │  On-Chain  │        │
│     │ (Trading)  │  │ (Metadata) │  │  Contracts │        │
│     └────────────┘  └────────────┘  └────────────┘        │
│                                             │               │
│                                             ▼               │
│                                    ┌────────────┐          │
│                                    │  Polygon   │          │
│                                    │ Blockchain │          │
│                                    └────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### CLOB (Central Limit Order Book) API

**Purpose**: Trading operations, order book data, position management

**Base URL**: `https://clob.polymarket.com`

**Key Concepts**:
- Hybrid-decentralized architecture
- Off-chain order matching
- On-chain settlement
- Signed order messages

#### Authentication

**HMAC-SHA256 Signature**:
```
Required Headers:
- POLY_API_KEY: Your public API key
- POLY_SIGNATURE: HMAC-SHA256 signature of request
- POLY_TIMESTAMP: Unix timestamp (30-second expiry)
- POLY_PASSPHRASE: Optional additional security
```

**Generating Credentials**:
```python
from py_clob_client.client import ClobClient

client = ClobClient(
    host="https://clob.polymarket.com",
    key="your-api-key",
    chain_id=137  # Polygon mainnet
)

# Generate API credentials
creds = client.create_api_creds()
```

#### Core Endpoints

**Public Endpoints (No Auth Required)**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/markets` | GET | List all active markets |
| `/markets/{id}` | GET | Market details |
| `/markets/{id}/orderbook` | GET | Order book with bids/asks |
| `/prices` | GET | Current prices |
| `/trades` | GET | Recent trade history |

**Authenticated Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orders` | POST | Create new order |
| `/orders/{id}` | DELETE | Cancel order |
| `/orders` | GET | List your orders |
| `/positions` | GET | Your positions |

#### Order Book Data Structure

```json
{
  "market": "0x123...",
  "asset_id": "outcome_token_id",
  "bids": [
    {"price": "0.58", "size": "1000"},
    {"price": "0.57", "size": "2500"}
  ],
  "asks": [
    {"price": "0.62", "size": "800"},
    {"price": "0.63", "size": "1200"}
  ],
  "spread": "0.04",
  "midpoint": "0.60"
}
```

#### Creating Orders

```python
from py_clob_client.client import ClobClient
from py_clob_client.order_builder.constants import BUY, SELL

# Initialize client
client = ClobClient(
    host="https://clob.polymarket.com",
    key="your-api-key",
    chain_id=137
)

# Create limit order
order = client.create_order(
    token_id="outcome_token_id",
    price=0.55,
    size=100,
    side=BUY
)

# Submit order
response = client.post_order(order)
```

### Gamma API

**Purpose**: Market metadata, resolution info, historical data

**Base URL**: `https://gamma-api.polymarket.com`

**Key Endpoints**:

| Endpoint | Description |
|----------|-------------|
| `/markets` | Market list with metadata |
| `/markets/{id}` | Full market details |
| `/events` | Event information |
| `/tags` | Market categories |

**Market Metadata Response**:
```json
{
  "id": "market_id",
  "question": "Will X happen by Y date?",
  "description": "Resolution criteria...",
  "outcomes": ["Yes", "No"],
  "end_date": "2025-12-31T23:59:59Z",
  "resolution_source": "Source URL",
  "volume": "1500000",
  "liquidity": "250000",
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

## Smart Contract Architecture

### Core Contracts

```
┌─────────────────────────────────────────────────────────────┐
│              POLYMARKET SMART CONTRACTS                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 CTF EXCHANGE                          │   │
│  │  Address: 0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E │   │
│  │                                                        │   │
│  │  Functions:                                            │   │
│  │  • fillOrder() - Execute trades                       │   │
│  │  • cancelOrder() - Cancel pending orders              │   │
│  │  • getOrderStatus() - Query order state               │   │
│  │                                                        │   │
│  │  For: Binary YES/NO markets                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            NEGRISK CTF EXCHANGE                       │   │
│  │  Address: 0xC5d563A36AE78145C45a50134d48A1215220f80a │   │
│  │                                                        │   │
│  │  For: Multi-outcome markets with negative risk        │   │
│  │  Features: Complex conditional logic                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               CONDITIONAL TOKENS                      │   │
│  │  Standard: ERC-1155                                   │   │
│  │                                                        │   │
│  │  • Outcome tokens (YES/NO shares)                     │   │
│  │  • Transferable and tradeable                         │   │
│  │  • Redeemable after resolution                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Transaction Template

Every Polymarket trade follows this structure:
- Max one group of matched orders per Polygon transaction
- Each set has exactly one taker
- Each set has at least one maker
- All receipts recorded on-chain

### Interacting with Contracts

```python
from web3 import Web3

# Connect to Polygon
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))

# CTF Exchange ABI (simplified)
CTF_EXCHANGE_ABI = [
    {
        "name": "fillOrder",
        "type": "function",
        "inputs": [...],
        "outputs": [...]
    }
]

# Contract instance
ctf_exchange = w3.eth.contract(
    address='0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E',
    abi=CTF_EXCHANGE_ABI
)
```

---

## On-Chain Data Analysis

### Dune Analytics Queries

**Available Dashboards**:

| Dashboard | Creator | Focus |
|-----------|---------|-------|
| Polymarket Activity | @filarm | Volume, users, trends |
| Polymarket Analysis | @lujanodera | Deep market analysis |
| CLOB Stats | @lifewillbeokay | Order book metrics |
| 2025 Capital & Whales | @thxshogun | Whale tracking |
| Trading Volume | @genejp999 | Volume breakdown |

**Sample SQL Query (Dune)**:
```sql
-- Daily trading volume
SELECT
    date_trunc('day', block_time) as day,
    SUM(amount_usd) as daily_volume,
    COUNT(DISTINCT trader) as unique_traders
FROM polymarket.trades
WHERE block_time > now() - interval '30 days'
GROUP BY 1
ORDER BY 1 DESC
```

### Key On-Chain Metrics

| Metric | Description | Query Approach |
|--------|-------------|----------------|
| Trading Volume | Total USDC traded | Sum transaction amounts |
| Open Interest | Outstanding positions | Token balances |
| Unique Traders | Distinct wallets | Count unique addresses |
| Whale Activity | Large transactions | Filter by amount threshold |
| Market Creation | New markets over time | Contract events |

---

## Python SDK Reference

### Installation

```bash
pip install py-clob-client
# Requires Python 3.9+
```

### Complete Trading Example

```python
from py_clob_client.client import ClobClient
from py_clob_client.order_builder.constants import BUY, SELL
import os

# Configuration
API_KEY = os.environ.get('POLYMARKET_API_KEY')
API_SECRET = os.environ.get('POLYMARKET_API_SECRET')
API_PASSPHRASE = os.environ.get('POLYMARKET_PASSPHRASE')

# Initialize client
client = ClobClient(
    host="https://clob.polymarket.com",
    key=API_KEY,
    secret=API_SECRET,
    passphrase=API_PASSPHRASE,
    chain_id=137
)

# Get markets
markets = client.get_markets()
print(f"Found {len(markets)} markets")

# Get specific market order book
market_id = "your_market_id"
orderbook = client.get_order_book(market_id)
print(f"Best bid: {orderbook['bids'][0]['price']}")
print(f"Best ask: {orderbook['asks'][0]['price']}")

# Get midpoint price
midpoint = client.get_midpoint(market_id)
print(f"Midpoint: {midpoint}")

# Create and submit order
order = client.create_order(
    token_id="outcome_token_id",
    price=0.55,
    size=100,
    side=BUY
)

# Post order
response = client.post_order(order)
print(f"Order ID: {response['orderID']}")

# Check positions
positions = client.get_positions()
for pos in positions:
    print(f"Token: {pos['token_id']}, Size: {pos['size']}")

# Cancel order
client.cancel_order(response['orderID'])
```

### Websocket Streaming

```python
import asyncio
import websockets
import json

async def stream_orderbook(market_id):
    uri = f"wss://ws-subscriptions-clob.polymarket.com/ws/market"

    async with websockets.connect(uri) as ws:
        # Subscribe to market
        subscribe_msg = {
            "type": "subscribe",
            "channel": "orderbook",
            "market": market_id
        }
        await ws.send(json.dumps(subscribe_msg))

        # Listen for updates
        async for message in ws:
            data = json.loads(message)
            print(f"Update: {data}")

# Run
asyncio.run(stream_orderbook("your_market_id"))
```

---

## Kalshi API Overview

### Authentication

Kalshi uses email/password authentication:

```python
import requests

# Login
response = requests.post(
    "https://trading-api.kalshi.com/trade-api/v2/login",
    json={
        "email": "your@email.com",
        "password": "your_password"
    }
)

token = response.json()['token']

# Use token in subsequent requests
headers = {"Authorization": f"Bearer {token}"}
```

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/markets` | GET | List markets |
| `/markets/{ticker}` | GET | Market details |
| `/markets/{ticker}/orderbook` | GET | Order book |
| `/portfolio/orders` | GET | Your orders |
| `/portfolio/orders` | POST | Create order |
| `/portfolio/positions` | GET | Your positions |

### Rate Limits

| Tier | Requests/Second |
|------|-----------------|
| Standard | 10 |
| Pro | 100 |

---

## Data Sources & Analytics Tools

### Third-Party Analytics

| Tool | URL | Features |
|------|-----|----------|
| PolymarketAnalytics | polymarketanalytics.com | Cross-platform comparison, arb finder |
| PolyTrack | polytrackhq.app | Whale tracking, alerts |
| Token Terminal | tokenterminal.com | Trading metrics |
| DeFi Rate | defirate.com/prediction-markets | Live tracker |
| Dune Analytics | dune.com | Custom SQL queries |

### Bitquery API

```graphql
# Query Polymarket trades
{
  EVM(network: matic) {
    DEXTrades(
      where: {
        Trade: {
          Dex: {
            SmartContract: {
              is: "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
            }
          }
        }
      }
    ) {
      Trade {
        Buy {
          Amount
          Currency {
            Symbol
          }
        }
        Sell {
          Amount
        }
      }
      Block {
        Time
      }
    }
  }
}
```

---

## Building a Trading Bot

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   TRADING BOT ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│   │    Data     │───►│  Strategy   │───►│  Execution  │    │
│   │  Ingestion  │    │   Layer     │    │   Engine    │    │
│   └─────────────┘    └─────────────┘    └─────────────┘    │
│         │                   │                   │           │
│   ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐      │
│   │• REST API │      │• Signals  │      │• Order    │      │
│   │• WebSocket│      │• Risk Mgmt│      │  routing  │      │
│   │• On-chain │      │• Position │      │• Fill     │      │
│   │  events   │      │  sizing   │      │  tracking │      │
│   └───────────┘      └───────────┘      └───────────┘      │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                    DATABASE                          │   │
│   │  • Trade history  • P&L tracking  • Market data     │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Sample Arbitrage Bot Structure

```python
import asyncio
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class MarketPrice:
    platform: str
    market_id: str
    yes_price: float
    no_price: float
    timestamp: float

class ArbitrageBot:
    def __init__(self):
        self.polymarket_client = PolymarketClient()
        self.kalshi_client = KalshiClient()
        self.min_spread = 0.03  # 3% minimum for profitability

    async def fetch_prices(self) -> Dict[str, MarketPrice]:
        """Fetch prices from all platforms"""
        poly_prices = await self.polymarket_client.get_prices()
        kalshi_prices = await self.kalshi_client.get_prices()
        return self.normalize_prices(poly_prices, kalshi_prices)

    def find_arbitrage(self, prices: Dict[str, MarketPrice]) -> List[dict]:
        """Identify arbitrage opportunities"""
        opportunities = []

        for market_id, platforms in prices.items():
            if 'polymarket' in platforms and 'kalshi' in platforms:
                poly = platforms['polymarket']
                kalshi = platforms['kalshi']

                # Check cross-platform arb
                spread = 1.0 - (poly.yes_price + kalshi.no_price)
                if spread > self.min_spread:
                    opportunities.append({
                        'market': market_id,
                        'buy_yes_on': 'polymarket',
                        'buy_no_on': 'kalshi',
                        'spread': spread
                    })

        return opportunities

    async def execute_arbitrage(self, opportunity: dict):
        """Execute arbitrage trade"""
        # Implementation depends on specific requirements
        pass

    async def run(self):
        """Main bot loop"""
        while True:
            try:
                prices = await self.fetch_prices()
                opportunities = self.find_arbitrage(prices)

                for opp in opportunities:
                    await self.execute_arbitrage(opp)

            except Exception as e:
                print(f"Error: {e}")

            await asyncio.sleep(1)  # 1 second polling

# Run bot
bot = ArbitrageBot()
asyncio.run(bot.run())
```

---

## Security Considerations

### API Key Management

```python
# NEVER hardcode credentials
# Use environment variables
import os

API_KEY = os.environ.get('POLYMARKET_API_KEY')
API_SECRET = os.environ.get('POLYMARKET_API_SECRET')

# Or use secrets manager
from aws_secretsmanager import get_secret
credentials = get_secret('polymarket-trading-credentials')
```

### Rate Limiting

```python
import time
from functools import wraps

def rate_limit(calls_per_second):
    min_interval = 1.0 / calls_per_second
    last_call = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_call[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(calls_per_second=10)
def api_call():
    # Your API call here
    pass
```

### Error Handling

```python
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def robust_api_call(endpoint):
    try:
        response = client.get(endpoint)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"API call failed: {e}")
        raise
```
