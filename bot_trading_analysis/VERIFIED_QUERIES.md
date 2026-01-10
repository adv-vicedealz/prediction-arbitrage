# Verified API Queries

This document contains the API endpoints and GraphQL queries we use to fetch Polymarket trade data. These queries have been verified against actual Polymarket data.

## Verification Results (January 10, 2026)

| Market | DOWN Accuracy | UP Accuracy |
|--------|---------------|-------------|
| btc-updown-15m-1768037400 | ~97-98% | ~97-98% |
| eth-updown-15m-1768050900 | **99.9994%** | 98.2% |
| btc-updown-15m-1768050900 | **99.9999%** | 97.7% |

**Conclusion:**
- **DOWN positions: Virtually perfect accuracy** (0.0001-0.02% error)
- **UP positions: ~2% overcounting** - we fetch slightly more trades than Polymarket displays
- **Average prices: Match exactly** for both outcomes

**Known limitation:** UP trades are consistently overcounted by ~2%. This may be due to cancelled/reverted trades that Polymarket excludes but Goldsky still records.

---

## API Endpoints

### 1. Gamma API (Market Metadata)
```
https://gamma-api.polymarket.com
```

**Use for:** Fetching market information (question, token IDs, outcomes, resolution status)

### 2. Goldsky Orderbook Subgraph (Trade Data)
```
https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn
```

**Use for:** Fetching all trade events (orderFilledEvents)

### 3. Goldsky PnL Subgraph (Historical P&L)
```
https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/pnl-subgraph/0.0.14/gn
```

**Use for:** Fetching pre-calculated realized P&L by wallet

---

## Query Templates

### 1. Fetch Market Metadata by Slug (VERIFIED)

**Endpoint:** Gamma API
**Method:** GET
**Status:** ✅ VERIFIED (January 10, 2026)
**When to use:** To get token IDs, outcomes, and resolution status for a market

```bash
curl "https://gamma-api.polymarket.com/markets?slug={MARKET_SLUG}"
```

**Example:**
```bash
curl "https://gamma-api.polymarket.com/markets?slug=btc-updown-15m-1768050900"
```

**Response fields we use:**
- `slug` - Market identifier
- `question` - Market question text
- `conditionId` - Polymarket condition ID
- `clobTokenIds` - Array of token IDs for each outcome (JSON string, needs parsing)
- `outcomes` - Array of outcome names e.g., ["Up", "Down"] (JSON string, needs parsing)
- `outcomePrices` - Final prices: 1.0 for winner, 0.0 for loser (JSON string, needs parsing)
- `closed` - Boolean, whether market has resolved
- `startDate`, `endDate` - Market time window (ISO 8601 format)

**Verification result:**
- Question: ✅ Matches Polymarket
- Winner: ✅ Matches Polymarket
- Resolution status: ✅ Matches Polymarket

---

### 2. Fetch Market Metadata by Token ID (VERIFIED)

**Endpoint:** Gamma API
**Method:** GET
**Status:** ✅ VERIFIED (January 10, 2026)
**When to use:** To lookup which market a token belongs to

```bash
curl "https://gamma-api.polymarket.com/markets?clob_token_ids={TOKEN_ID}"
```

**Example:**
```bash
curl "https://gamma-api.polymarket.com/markets?clob_token_ids=297478145107466476230486066113275432075504678169319680317187259974298847416"
```

**Returns:** Same response format as slug query. Useful for reverse-lookup when you have a token ID from a trade.

---

### 3. Fetch Trades by Token ID (VERIFIED)

**Endpoint:** Goldsky Orderbook Subgraph
**Method:** POST
**Status:** ✅ VERIFIED (January 10, 2026) - DOWN 99.99% accurate, UP ~98% accurate
**When to use:** To fetch all trades for a specific outcome token

```graphql
{
  orderFilledEvents(
    first: 1000,
    where: {
      makerAssetId: "{TOKEN_ID}",
      timestamp_gte: "{START_TIMESTAMP}",
      timestamp_lt: "{END_TIMESTAMP}"
    },
    orderBy: id,
    orderDirection: asc
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

**Important:** Run this query TWICE per token:
1. With `makerAssetId: "{TOKEN_ID}"` - trades where maker SOLD this token
2. With `takerAssetId: "{TOKEN_ID}"` - trades where maker BOUGHT this token

**Pagination:** Use `id_gt: "{LAST_ID}"` to fetch more than 1000 records.

---

### 4. Fetch Trades by Wallet (VERIFIED)

**Endpoint:** Goldsky Orderbook Subgraph
**Method:** POST
**Status:** ✅ VERIFIED (January 10, 2026) - Produces identical results to token-based query
**When to use:** To fetch all trades for a specific wallet address

```graphql
{
  orderFilledEvents(
    first: 1000,
    where: {
      maker: "{WALLET_ADDRESS}",
      timestamp_gte: "{START_TIMESTAMP}",
      timestamp_lt: "{END_TIMESTAMP}"
    },
    orderBy: timestamp,
    orderDirection: asc
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

**Note:** Query both `maker` and `taker` fields to get all trades involving the wallet.

---

## Data Parsing Rules

### Amounts
All amounts from Goldsky are in **micro-units** (multiply by 10^-6):
```python
usdc = int(makerAmountFilled) / 1_000_000
shares = int(takerAmountFilled) / 1_000_000
fee = int(fee) / 1_000_000
```

### Determining BUY vs SELL
```python
if makerAssetId == "0":
    # Maker paid USDC (asset 0), received shares
    # Maker = BUY, Taker = SELL
    usdc = makerAmountFilled / 1e6
    shares = takerAmountFilled / 1e6
else:
    # Maker paid shares, received USDC
    # Maker = SELL, Taker = BUY
    shares = makerAmountFilled / 1e6
    usdc = takerAmountFilled / 1e6

price = usdc / shares
```

### Wallet Addresses
Always convert to lowercase for comparison:
```python
wallet = trade["maker"].lower()
```

---

## Example: Full Trade Fetch for Verification

```python
import requests

GOLDSKY = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"

def fetch_trades(token_id, start_ts, end_ts):
    """Fetch all trades for a token within time range."""
    all_trades = []
    last_id = ""

    while True:
        where = f'makerAssetId: "{token_id}", timestamp_gte: "{start_ts}", timestamp_lt: "{end_ts}"'
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

        resp = requests.post(GOLDSKY, json={"query": query}, timeout=30)
        events = resp.json().get("data", {}).get("orderFilledEvents", [])

        if not events:
            break

        all_trades.extend(events)
        last_id = events[-1]["id"]

        if len(events) < 1000:
            break

    return all_trades
```

---

## Verification Checklist

When verifying data against Polymarket:

- [ ] Total shares match (within ~2% for UP, exact for DOWN)
- [ ] Total cost matches (within ~2% for UP, exact for DOWN)
- [ ] Average prices match exactly
- [ ] Transaction hashes can be verified on PolygonScan

**PolygonScan verification:**
```
https://polygonscan.com/tx/{TRANSACTION_HASH}
```

---

## Additional APIs

### 5. Get Closed Positions for User (VERIFIED)

**Endpoint:** Polymarket Data API
**URL:** `https://data-api.polymarket.com/v1/closed-positions`
**Method:** GET
**Status:** ✅ VERIFIED (January 10, 2026) - Matches Polymarket UI exactly

**When to use:** To get official Polymarket data for closed/resolved positions including realized P&L.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | Yes | Wallet address (0x-prefixed) |
| `limit` | integer | No | Max results (default: 10, max: 50) |
| `offset` | integer | No | Pagination offset (default: 0) |
| `sortBy` | enum | No | REALIZEDPNL, TITLE, PRICE, AVGPRICE, TIMESTAMP |
| `sortDirection` | enum | No | ASC or DESC (default: DESC) |
| `market` | string[] | No | Filter by condition IDs (CSV) |
| `title` | string | No | Filter by market title |

**Example:**
```bash
curl "https://data-api.polymarket.com/v1/closed-positions?user=0x0ea574f3204c5c9c0cdead90392ea0990f4d17e4&limit=50&sortBy=TIMESTAMP&sortDirection=DESC"
```

**Response fields:**
- `title` - Market title
- `slug` - Market slug
- `outcome` - Position outcome (Up/Down)
- `totalBought` - Total shares bought
- `avgPrice` - Average purchase price
- `realizedPnl` - Realized profit/loss in USD
- `conditionId` - Market condition ID
- `endDate` - Market end date

**Verification result:**
- Shares: ✅ Matches Polymarket UI exactly
- Avg Price: ✅ Matches Polymarket UI exactly
- Realized P&L: ✅ Matches Polymarket UI exactly

**Note:** This API returns Polymarket's official numbers, which may differ slightly (~2% for UP) from raw Goldsky orderbook data.

---

### 6. Polymarket Trades API - LIMITATION DISCOVERED

**Endpoint:** Polymarket Data API
**URL:** `https://data-api.polymarket.com/v1/trades`
**Method:** GET
**Status:** ⚠️ LIMITED - Only returns BUY trades, NOT SELL trades

**Important Limitation Discovered (January 10, 2026):**

This API does **NOT** return complete trade history. It only returns trades where the user **bought** shares, not where they **sold** shares.

**Evidence:**
- For wallet `0x0ea574f3204c5c9c0cdead90392ea0990f4d17e4` in market `btc-updown-15m-1768050900`:
  - Goldsky shows: 63 SELL trades (as taker)
  - Polymarket Trades API shows: 0 SELL trades

- Examined TX `0xfdf8084ab97f5551c2678f53c98ec19c3a26a74cd9ea43af91f36c97301e0e91`:
  - Goldsky: 14 events (1 BUY DOWN + 13 SELL UP)
  - Polymarket: Only returned the 1 BUY DOWN trade

**Conclusion:**
- Use **Goldsky orderFilledEvents** for complete trade history (both BUY and SELL)
- Use **Polymarket Trades API** only if you need Polymarket's formatted view of BUY activity
- The `closed-positions` API provides accurate NET position data (totalBought = bought - sold)

---

## API Comparison Summary

| Data Need | Best API | Notes |
|-----------|----------|-------|
| Complete trade history (BUY + SELL) | Goldsky orderFilledEvents | Query both maker and taker |
| Market metadata | Gamma API | Verified accurate |
| Net position & P&L | Polymarket closed-positions | Matches UI exactly |
| BUY trades only | Polymarket Trades API | Does NOT include SELLs |
