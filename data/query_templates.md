# Polymarket Analysis Query Templates

This document contains all the queries used to analyze wallet activity on Polymarket markets using Goldsky Subgraph API.

---

## 1. Get Market Details from Gamma API

### By Event Slug
```bash
curl -s "https://gamma-api.polymarket.com/events?slug=YOUR_MARKET_SLUG" | python3 -m json.tool
```

**Example:**
```bash
curl -s "https://gamma-api.polymarket.com/events?slug=btc-updown-15m-1767960000" | python3 -m json.tool
```

**Returns:** Market details including `clobTokenIds` (token IDs for Yes/No outcomes), resolution status, volume, etc.

### By Token ID
```bash
curl -s "https://gamma-api.polymarket.com/markets?clob_token_ids=YOUR_TOKEN_ID" | python3 -m json.tool
```

---

## 2. Goldsky Subgraph Queries

**Base Endpoint:**
```
https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn
```

### 2.1 Fetch Maker Buy Orders (Limit Orders to Buy)

When wallet places limit buy order (pays USDC, receives shares):

```bash
WALLET="0xYOUR_WALLET_ADDRESS"
TOKEN_ID="YOUR_TOKEN_ID"

curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\", takerAssetId: \\\"$TOKEN_ID\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}"
```

### 2.2 Fetch Maker Sell Orders (Limit Orders to Sell)

When wallet places limit sell order (pays shares, receives USDC):

```bash
WALLET="0xYOUR_WALLET_ADDRESS"
TOKEN_ID="YOUR_TOKEN_ID"

curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\", makerAssetId: \\\"$TOKEN_ID\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}"
```

### 2.3 Fetch Taker Buy Orders (Market Orders to Buy)

When wallet takes from orderbook (buys shares):

```bash
WALLET="0xYOUR_WALLET_ADDRESS"
TOKEN_ID="YOUR_TOKEN_ID"

curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { taker: \\\"$WALLET\\\", makerAssetId: \\\"$TOKEN_ID\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}"
```

### 2.4 Fetch Taker Sell Orders (Market Orders to Sell)

When wallet takes from orderbook (sells shares):

```bash
WALLET="0xYOUR_WALLET_ADDRESS"
TOKEN_ID="YOUR_TOKEN_ID"

curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { taker: \\\"$WALLET\\\", takerAssetId: \\\"$TOKEN_ID\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}"
```

---

## 3. Complete Fetch Script Template

Copy and modify these variables to fetch all trades for a wallet on a specific market:

```bash
# ============================================
# CONFIGURATION - MODIFY THESE VALUES
# ============================================
WALLET="0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
UP_TOKEN="YOUR_UP_TOKEN_ID"
DOWN_TOKEN="YOUR_DOWN_TOKEN_ID"
OUTPUT_DIR="/tmp/market_analysis"

# ============================================
# CREATE OUTPUT DIRECTORY
# ============================================
mkdir -p $OUTPUT_DIR

# ============================================
# FETCH ALL 8 TRADE TYPES
# ============================================

echo "=== Fetching maker trades buying Up tokens ==="
curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\", takerAssetId: \\\"$UP_TOKEN\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}" \
  > $OUTPUT_DIR/maker_buy_up.json

echo "=== Fetching maker trades selling Up tokens ==="
curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\", makerAssetId: \\\"$UP_TOKEN\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}" \
  > $OUTPUT_DIR/maker_sell_up.json

echo "=== Fetching taker trades buying Up tokens ==="
curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { taker: \\\"$WALLET\\\", makerAssetId: \\\"$UP_TOKEN\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}" \
  > $OUTPUT_DIR/taker_buy_up.json

echo "=== Fetching taker trades selling Up tokens ==="
curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { taker: \\\"$WALLET\\\", takerAssetId: \\\"$UP_TOKEN\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}" \
  > $OUTPUT_DIR/taker_sell_up.json

echo "=== Fetching maker trades buying Down tokens ==="
curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\", takerAssetId: \\\"$DOWN_TOKEN\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}" \
  > $OUTPUT_DIR/maker_buy_down.json

echo "=== Fetching maker trades selling Down tokens ==="
curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\", makerAssetId: \\\"$DOWN_TOKEN\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}" \
  > $OUTPUT_DIR/maker_sell_down.json

echo "=== Fetching taker trades buying Down tokens ==="
curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { taker: \\\"$WALLET\\\", makerAssetId: \\\"$DOWN_TOKEN\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}" \
  > $OUTPUT_DIR/taker_buy_down.json

echo "=== Fetching taker trades selling Down tokens ==="
curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { taker: \\\"$WALLET\\\", takerAssetId: \\\"$DOWN_TOKEN\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}" \
  > $OUTPUT_DIR/taker_sell_down.json

# ============================================
# COUNT RESULTS
# ============================================
echo ""
echo "=== Trade counts ==="
echo "Maker buy Up: $(cat $OUTPUT_DIR/maker_buy_up.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('orderFilledEvents',[])))")"
echo "Maker sell Up: $(cat $OUTPUT_DIR/maker_sell_up.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('orderFilledEvents',[])))")"
echo "Taker buy Up: $(cat $OUTPUT_DIR/taker_buy_up.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('orderFilledEvents',[])))")"
echo "Taker sell Up: $(cat $OUTPUT_DIR/taker_sell_up.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('orderFilledEvents',[])))")"
echo "Maker buy Down: $(cat $OUTPUT_DIR/maker_buy_down.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('orderFilledEvents',[])))")"
echo "Maker sell Down: $(cat $OUTPUT_DIR/maker_sell_down.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('orderFilledEvents',[])))")"
echo "Taker buy Down: $(cat $OUTPUT_DIR/taker_buy_down.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('orderFilledEvents',[])))")"
echo "Taker sell Down: $(cat $OUTPUT_DIR/taker_sell_down.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('orderFilledEvents',[])))")"
```

---

## 4. Query with Time Range Filter

Add timestamp filters to limit results to a specific time window:

```bash
# Convert dates to Unix timestamps (seconds)
# January 8, 2026 00:00:00 UTC = 1767826800
# January 9, 2026 00:00:00 UTC = 1767913200

START_TS="1767826800"
END_TS="1767913200"

curl -s -X POST 'https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn' \
  -H 'Content-Type: application/json' \
  -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\", takerAssetId: \\\"$TOKEN_ID\\\", timestamp_gte: \\\"$START_TS\\\", timestamp_lt: \\\"$END_TS\\\" }, orderBy: timestamp, orderDirection: asc) { id transactionHash timestamp maker taker makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }\"}"
```

---

## 5. Pagination for Large Results

If more than 1000 results, use cursor-based pagination with `id_gt`:

```bash
LAST_ID=""  # Empty for first request

# First request
curl -s -X POST '...' -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\" }, orderBy: id, orderDirection: asc) { id ... } }\"}"

# Get last ID from response, then:
LAST_ID="0xabc123..."

# Subsequent requests - add id_gt filter
curl -s -X POST '...' -d "{\"query\": \"{ orderFilledEvents(first: 1000, where: { maker: \\\"$WALLET\\\", id_gt: \\\"$LAST_ID\\\" }, orderBy: id, orderDirection: asc) { id ... } }\"}"
```

---

## 6. Field Reference

### OrderFilledEvent Fields

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
    → Maker paid USDC, received shares = MAKER BUY
    → usdc = makerAmountFilled / 1e6
    → shares = takerAmountFilled / 1e6

If makerAssetId != "0":
    → Maker paid shares, received USDC = MAKER SELL
    → shares = makerAmountFilled / 1e6
    → usdc = takerAmountFilled / 1e6

Price = usdc / shares
```

---

## 7. Key Metrics Formulas

### Cost Per Pair (Arbitrage Check)
```python
cost_per_pair = (usdc_spent_on_yes + usdc_spent_on_no) / (total_shares / 2)

# If cost_per_pair < $1.00: Potential arbitrage (but check fees!)
# If cost_per_pair >= $1.00: Guaranteed loss
```

### P&L Calculation
```python
# For binary market where Yes=$1 if wins, No=$1 if wins

yes_pnl = (yes_net_position * yes_resolution_price) - yes_usdc_spent + yes_usdc_received
no_pnl = (no_net_position * no_resolution_price) - no_usdc_spent + no_usdc_received
total_pnl = yes_pnl + no_pnl - total_fees

# Example: Yes won
yes_resolution_price = 1.0
no_resolution_price = 0.0
```

### Net Position
```python
net_position = shares_bought - shares_sold
```

---

## 8. Example Token IDs

### BTC Up/Down 6:00AM-6:15AM ET (Jan 9, 2026)
- Up: `65689469986114736683609567440585706468061828613693669084008270331829703859210`
- Down: `19004630472054155562446266004006762878910712196312117007145993767241545797916`

### BTC Up/Down 7:00AM-7:15AM ET (Jan 9, 2026)
- Up: `87304645790574900638549749492944305962862555498267305581482152654804844703949`
- Down: `106294959112031011990994190045757964617482382645413391634509092547535732907684`

---

## 9. Quick Reference: All Subgraphs

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
