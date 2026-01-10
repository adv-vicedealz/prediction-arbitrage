#

 Polymarket Trade Data Fetching Methodology

This document describes how to fetch complete trade history for any Polymarket user using the Goldsky Subgraph API.

---

## Why Goldsky Subgraph?

| Method | Offset Limit | Rate Limit | Best For |
|--------|--------------|------------|----------|
| **Goldsky Subgraph** | None (cursor-based) | Generous | High-frequency traders |
| Data API `/activity` | 10,000 max | 1,000/10s | <10K trades |
| Direct RPC | None | Varies | Raw blockchain data |

For users like gabagool22 with **100K+ trades/day**, the Goldsky Subgraph is the only practical option.

---

## Available Subgraphs

Polymarket has 5 subgraphs hosted on Goldsky:

| Subgraph | Endpoint | Use Case |
|----------|----------|----------|
| **Orderbook** | `orderbook-subgraph/0.0.1` | Trades, OrderFilled events |
| Activity | `activity-subgraph/0.0.4` | Splits, merges, redemptions |
| Positions | `positions-subgraph/0.0.7` | User positions, PnL |
| Open Interest | `oi-subgraph/0.0.6` | Market open interest |
| PnL | `pnl-subgraph/0.0.14` | Profit/loss calculations |

**Base URL:**
```
https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/{subgraph}/gn
```

---

## Step 1: Explore the Schema

### Query Available Entities

```bash
curl -s -X POST \
  'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d '{"query": "{ __schema { queryType { fields { name } } } }"}'
```

**Response:**
```json
{
  "data": {
    "__schema": {
      "queryType": {
        "fields": [
          {"name": "marketData"},
          {"name": "marketDatas"},
          {"name": "orderFilledEvent"},
          {"name": "orderFilledEvents"},
          {"name": "ordersMatchedEvent"},
          {"name": "ordersMatchedEvents"},
          {"name": "orderbook"},
          {"name": "orderbooks"},
          {"name": "ordersMatchedGlobal"},
          {"name": "ordersMatchedGlobals"},
          {"name": "_meta"}
        ]
      }
    }
  }
}
```

### Query Entity Fields

```bash
curl -s -X POST \
  'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d '{"query": "{ __type(name: \"OrderFilledEvent\") { fields { name type { name kind ofType { name } } } } }"}'
```

**Response - OrderFilledEvent Fields:**
```json
{
  "fields": [
    {"name": "id", "type": "ID"},
    {"name": "transactionHash", "type": "Bytes"},
    {"name": "timestamp", "type": "BigInt"},
    {"name": "orderHash", "type": "Bytes"},
    {"name": "maker", "type": "String"},
    {"name": "taker", "type": "String"},
    {"name": "makerAssetId", "type": "String"},
    {"name": "takerAssetId", "type": "String"},
    {"name": "makerAmountFilled", "type": "BigInt"},
    {"name": "takerAmountFilled", "type": "BigInt"},
    {"name": "fee", "type": "BigInt"}
  ]
}
```

---

## Step 2: Fetch Trades by User

### Basic Query - Maker Trades

Fetch trades where the user was the **maker** (placed limit orders):

```graphql
{
  orderFilledEvents(
    first: 1000,
    where: {
      maker: "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d",
      timestamp_gte: "1767826800",
      timestamp_lt: "1767913200"
    },
    orderBy: timestamp,
    orderDirection: desc
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
    fee
  }
}
```

### Basic Query - Taker Trades

Fetch trades where the user was the **taker** (took from orderbook):

```graphql
{
  orderFilledEvents(
    first: 1000,
    where: {
      taker: "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d",
      timestamp_gte: "1767826800",
      timestamp_lt: "1767913200"
    },
    orderBy: timestamp,
    orderDirection: desc
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
    fee
  }
}
```

### Timestamp Calculation

Convert dates to Unix timestamps (seconds):

```python
from datetime import datetime

# January 8, 2026 00:00:00 UTC
start_ts = int(datetime(2026, 1, 8, 0, 0, 0).timestamp())  # 1767826800

# January 9, 2026 00:00:00 UTC
end_ts = int(datetime(2026, 1, 9, 0, 0, 0).timestamp())    # 1767913200
```

---

## Step 3: Pagination with Cursor

The subgraph has a **1000 record limit per query**. Use cursor-based pagination with `id_gt`:

### Pagination Strategy

```graphql
# First request
{
  orderFilledEvents(
    first: 1000,
    where: { maker: "0x...", timestamp_gte: "START", timestamp_lt: "END" },
    orderBy: id,
    orderDirection: asc
  ) { id ... }
}

# Subsequent requests - use last ID as cursor
{
  orderFilledEvents(
    first: 1000,
    where: {
      maker: "0x...",
      timestamp_gte: "START",
      timestamp_lt: "END",
      id_gt: "LAST_ID_FROM_PREVIOUS_BATCH"
    },
    orderBy: id,
    orderDirection: asc
  ) { id ... }
}
```

---

## Step 4: Complete Python Implementation

### Fetch All Maker Trades

```python
import requests
import json

ENDPOINT = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"

def fetch_maker_trades(wallet: str, start_ts: int, end_ts: int) -> list:
    """
    Fetch all trades where wallet was the maker (limit orders).
    Uses cursor-based pagination to bypass limits.
    """
    wallet = wallet.lower()
    all_trades = []
    last_id = ""
    batch_num = 0

    while True:
        batch_num += 1

        # Build where clause
        where = f'maker: "{wallet}", timestamp_gte: "{start_ts}", timestamp_lt: "{end_ts}"'
        if last_id:
            where += f', id_gt: "{last_id}"'

        query = f'''{{
            orderFilledEvents(
                first: 1000,
                where: {{ {where} }},
                orderBy: id,
                orderDirection: asc
            ) {{
                id
                transactionHash
                timestamp
                maker
                taker
                makerAssetId
                takerAssetId
                makerAmountFilled
                takerAmountFilled
                fee
            }}
        }}'''

        resp = requests.post(ENDPOINT, json={"query": query}, timeout=30)
        data = resp.json()

        if "errors" in data:
            print(f"Error: {data['errors']}")
            break

        events = data["data"]["orderFilledEvents"]
        if not events:
            break

        all_trades.extend(events)
        last_id = events[-1]["id"]

        print(f"Batch {batch_num}: fetched {len(events)} trades (total: {len(all_trades)})")

        if len(events) < 1000:
            break

    return all_trades


def fetch_taker_trades(wallet: str, start_ts: int, end_ts: int) -> list:
    """
    Fetch all trades where wallet was the taker (market orders).
    """
    wallet = wallet.lower()
    all_trades = []
    last_id = ""
    batch_num = 0

    while True:
        batch_num += 1

        where = f'taker: "{wallet}", timestamp_gte: "{start_ts}", timestamp_lt: "{end_ts}"'
        if last_id:
            where += f', id_gt: "{last_id}"'

        query = f'''{{
            orderFilledEvents(
                first: 1000,
                where: {{ {where} }},
                orderBy: id,
                orderDirection: asc
            ) {{
                id
                transactionHash
                timestamp
                maker
                taker
                makerAssetId
                takerAssetId
                makerAmountFilled
                takerAmountFilled
                fee
            }}
        }}'''

        resp = requests.post(ENDPOINT, json={"query": query}, timeout=30)
        data = resp.json()

        if "errors" in data:
            break

        events = data["data"]["orderFilledEvents"]
        if not events:
            break

        all_trades.extend(events)
        last_id = events[-1]["id"]

        print(f"Batch {batch_num}: fetched {len(events)} trades (total: {len(all_trades)})")

        if len(events) < 1000:
            break

    return all_trades


# Example usage
if __name__ == "__main__":
    WALLET = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
    START_TS = 1767826800  # Jan 8, 2026 00:00:00
    END_TS = 1767913200    # Jan 9, 2026 00:00:00

    print("Fetching maker trades...")
    maker_trades = fetch_maker_trades(WALLET, START_TS, END_TS)

    print("\nFetching taker trades...")
    taker_trades = fetch_taker_trades(WALLET, START_TS, END_TS)

    print(f"\nTotal maker trades: {len(maker_trades)}")
    print(f"Total taker trades: {len(taker_trades)}")
    print(f"Total all trades: {len(maker_trades) + len(taker_trades)}")

    # Save to files
    with open("maker_trades.json", "w") as f:
        json.dump(maker_trades, f, indent=2)

    with open("taker_trades.json", "w") as f:
        json.dump(taker_trades, f, indent=2)
```

---

## Step 5: Enrich with Market Metadata

The raw trade data only contains token IDs. To get market names and outcomes, query the Gamma API:

### Gamma API Query

```python
import requests
import json
import time

GAMMA_API = "https://gamma-api.polymarket.com/markets"

def get_market_metadata(token_id: str) -> dict:
    """
    Fetch market metadata for a token ID.
    Returns question, outcomes, category, etc.
    """
    try:
        resp = requests.get(
            GAMMA_API,
            params={"clob_token_ids": token_id},
            timeout=10
        )
        markets = resp.json()

        if markets and len(markets) > 0:
            m = markets[0]

            # Parse outcomes and token IDs
            outcomes = m.get("outcomes", '["Yes", "No"]')
            clob_ids = m.get("clobTokenIds", "[]")

            if isinstance(outcomes, str):
                outcomes = json.loads(outcomes)
            if isinstance(clob_ids, str):
                clob_ids = json.loads(clob_ids)

            # Determine which outcome this token represents
            outcome = "Unknown"
            if len(clob_ids) >= 2 and len(outcomes) >= 2:
                if token_id == clob_ids[0]:
                    outcome = outcomes[0]
                elif token_id == clob_ids[1]:
                    outcome = outcomes[1]

            return {
                "question": m.get("question"),
                "slug": m.get("slug"),
                "category": m.get("category"),
                "conditionId": m.get("conditionId"),
                "outcome": outcome,
                "endDate": m.get("endDate"),
                "outcomes": outcomes,
                "clobTokenIds": clob_ids
            }
    except Exception as e:
        print(f"Error fetching metadata: {e}")

    return {}


def enrich_trades(trades: list) -> list:
    """
    Add market metadata to trades.
    Caches results to avoid duplicate API calls.
    """
    # Get unique token IDs
    token_ids = set()
    for t in trades:
        if t["makerAssetId"] != "0":
            token_ids.add(t["makerAssetId"])
        if t["takerAssetId"] != "0":
            token_ids.add(t["takerAssetId"])

    print(f"Fetching metadata for {len(token_ids)} unique tokens...")

    # Fetch metadata for each token
    token_metadata = {}
    for i, token_id in enumerate(token_ids):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(token_ids)}")

        token_metadata[token_id] = get_market_metadata(token_id)
        time.sleep(0.05)  # Rate limit

    # Enrich trades
    enriched = []
    for t in trades:
        # Determine side and token
        if t["makerAssetId"] == "0":
            side = "BUY"
            token_id = t["takerAssetId"]
            usdc = int(t["makerAmountFilled"]) / 1e6
            shares = int(t["takerAmountFilled"]) / 1e6
        else:
            side = "SELL"
            token_id = t["makerAssetId"]
            usdc = int(t["takerAmountFilled"]) / 1e6
            shares = int(t["makerAmountFilled"]) / 1e6

        price = usdc / shares if shares > 0 else 0
        metadata = token_metadata.get(token_id, {})

        enriched.append({
            "timestamp": t["timestamp"],
            "transactionHash": t["transactionHash"],
            "side": side,
            "usdc": round(usdc, 2),
            "shares": round(shares, 2),
            "price": round(price, 4),
            "token_id": token_id,
            "question": metadata.get("question"),
            "outcome": metadata.get("outcome"),
            "conditionId": metadata.get("conditionId"),
            "category": metadata.get("category")
        })

    return enriched
```

---

## Field Reference

### Raw Trade Fields (from Subgraph)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique event ID (txHash + orderHash) |
| `transactionHash` | string | Polygon transaction hash |
| `timestamp` | string | Unix timestamp in seconds |
| `maker` | string | Wallet that placed the limit order |
| `taker` | string | Wallet that filled the order |
| `makerAssetId` | string | Asset ID maker paid (`0` = USDC) |
| `takerAssetId` | string | Asset ID taker paid (`0` = USDC) |
| `makerAmountFilled` | string | Amount maker paid (divide by 1e6) |
| `takerAmountFilled` | string | Amount taker paid (divide by 1e6) |
| `fee` | string | Fee in wei (divide by 1e6) |

### Interpreting Trade Direction

```
If makerAssetId == "0":
    → Maker paid USDC, received shares = BUY
    → usdc = makerAmountFilled / 1e6
    → shares = takerAmountFilled / 1e6
    → price = usdc / shares

If makerAssetId != "0":
    → Maker paid shares, received USDC = SELL
    → shares = makerAmountFilled / 1e6
    → usdc = takerAmountFilled / 1e6
    → price = usdc / shares
```

### Enriched Trade Fields

| Field | Description |
|-------|-------------|
| `timestamp` | ISO format datetime |
| `transactionHash` | Polygon tx hash |
| `side` | BUY or SELL |
| `usdc` | USDC amount |
| `shares` | Number of shares |
| `price` | Price per share |
| `token_id` | Polymarket token ID |
| `question` | Market question text |
| `outcome` | Up, Down, Yes, No, etc. |
| `conditionId` | Market condition ID |
| `category` | Market category |

---

## Quick Reference - cURL Commands

### Fetch Maker Trades (Single Batch)

```bash
curl -s -X POST \
  'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "{ orderFilledEvents(first: 1000, where: { maker: \"0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d\", timestamp_gte: \"1767826800\", timestamp_lt: \"1767913200\" }, orderBy: id, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }"
  }'
```

### Fetch Taker Trades (Single Batch)

```bash
curl -s -X POST \
  'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "{ orderFilledEvents(first: 1000, where: { taker: \"0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d\", timestamp_gte: \"1767826800\", timestamp_lt: \"1767913200\" }, orderBy: id, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }"
  }'
```

### Get Market Metadata

```bash
curl -s "https://gamma-api.polymarket.com/markets?clob_token_ids=TOKEN_ID_HERE"
```

---

## Performance Results

For gabagool22 on January 8, 2026:

| Metric | Value |
|--------|-------|
| Maker trades fetched | 106,747 |
| Taker trades fetched | 34,427 |
| Total trades | 141,174 |
| Unique tokens | 480 |
| Batches required (maker) | 107 |
| Batches required (taker) | 35 |
| Total fetch time | ~3 minutes |

---

## Data Files Generated

| File | Description |
|------|-------------|
| `jan8_trades.json` | Raw maker trades from subgraph |
| `jan8_taker_trades.json` | Raw taker trades from subgraph |
| `token_metadata.json` | Token ID → market metadata mapping |
| `jan8_enriched.json` | All trades with market metadata |

---

## Troubleshooting

### "No data returned"
- Check wallet address is lowercase
- Verify timestamps are in seconds (not milliseconds)
- Ensure timestamp range has activity

### "Rate limited"
- Add `time.sleep(0.1)` between requests
- Goldsky is generous but not unlimited

### "Missing market metadata"
- Some tokens may be from old/delisted markets
- Gamma API may not have all historical markets

---

## Alternative: Data API (for <10K trades)

If the user has fewer than 10,000 trades, the simpler Data API works:

```python
import requests

def fetch_trades_data_api(wallet: str, days: int = 7) -> list:
    """Simple approach for low-volume users."""
    import time

    end_ts = int(time.time())
    start_ts = end_ts - (days * 86400)

    all_trades = []
    offset = 0

    while offset < 10000:
        resp = requests.get(
            "https://data-api.polymarket.com/activity",
            params={
                "user": wallet,
                "start": start_ts,
                "end": end_ts,
                "type": "TRADE",
                "limit": 500,
                "offset": offset
            }
        )

        trades = resp.json()
        if not trades:
            break

        all_trades.extend(trades)
        offset += 500
        time.sleep(0.1)

    return all_trades
```

**Limitation:** Max 10,000 trades due to offset cap.

---

*Documentation for Polymarket trade data fetching via Goldsky Subgraph*
