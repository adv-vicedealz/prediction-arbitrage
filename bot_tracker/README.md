# Bot Trading Tracker

Real-time trading tracker with web dashboard to analyze how bot wallets operate on Polymarket's 15-minute BTC/ETH Up/Down markets.

## Features

- **Real-time trade streaming**: Polls Goldsky every 5 seconds for new trades from target wallets
- **Position tracking**: Maintains running UP/DOWN shares, edge, and hedge ratio per wallet
- **Pattern detection**: Analyzes timing, price strategies, and hedging behavior
- **Web dashboard**: Live-updating React dashboard with WebSocket updates
- **REST API**: Full API for querying positions, trades, and patterns

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Goldsky API ──► Trade Poller (5s) ──► Position Tracker        │
│       │                │                      │                 │
│       │                └──────────────────────┼──► Pattern      │
│       │                                       │    Detector     │
│  CLOB API ──► Market Context ─────────────────┘                 │
│                                                                  │
│       └───────────────► WebSocket Server ──► React Dashboard   │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### Backend

```bash
cd bot_tracker
pip install -r requirements.txt
```

### Frontend

```bash
cd bot_tracker/dashboard
npm install
```

## Usage

### Start the Backend

```bash
# From the prediction-arbitrage directory
python -m bot_tracker.main
```

This starts:
- HTTP API at `http://localhost:8000`
- WebSocket server at `ws://localhost:8765`
- API docs at `http://localhost:8000/docs`

### Start the Frontend

```bash
cd bot_tracker/dashboard
npm run dev
```

Dashboard runs at `http://localhost:3000`

## Target Wallets

| Address | Name |
|---------|------|
| `0x589222a5...` | PurpleThunderBicycleMountain |
| `0x0ea574f3...` | Wallet_0ea574 |
| `0xd0d6053c...` | k9Q2mX4L8A7ZP3R |
| `0x63ce3421...` | 0x8dxd |

## API Endpoints

### Status
- `GET /` - API info
- `GET /api/status` - Tracker status

### Wallets
- `GET /api/wallets` - List tracked wallets
- `GET /api/wallets/{wallet}/positions` - Wallet positions
- `GET /api/wallets/{wallet}/trades` - Wallet trades

### Positions
- `GET /api/positions` - All positions
- `GET /api/positions/{wallet}/{market}` - Specific position

### Markets
- `GET /api/markets` - All markets
- `GET /api/markets/active` - Active markets
- `GET /api/markets/{slug}` - Specific market

### Trades
- `GET /api/trades` - Recent trades
- `GET /api/trades/{market}` - Market trades

### Patterns
- `GET /api/patterns/{wallet}/{market}` - Full pattern analysis
- `GET /api/patterns/{wallet}/{market}/timing` - Timing patterns
- `GET /api/patterns/{wallet}/{market}/price` - Price patterns
- `GET /api/patterns/{wallet}/{market}/hedge` - Hedge patterns

## WebSocket Events

Connect to `ws://localhost:8765` to receive:

- `trade` - New trade event
- `position` - Position update
- `market` - Market context update
- `pattern_timing` - Timing pattern update
- `pattern_price` - Price pattern update
- `pattern_hedge` - Hedge pattern update
- `stats` - Tracker statistics

## Data Models

### TradeEvent
```json
{
  "id": "...",
  "tx_hash": "0x...",
  "timestamp": 1234567890,
  "wallet": "0x...",
  "wallet_name": "PurpleThunder...",
  "role": "maker",
  "side": "BUY",
  "outcome": "Up",
  "shares": 100.0,
  "usdc": 48.0,
  "price": 0.48,
  "market_slug": "btc-updown-15m-..."
}
```

### WalletPosition
```json
{
  "wallet": "0x...",
  "market_slug": "...",
  "up_shares": 500.0,
  "down_shares": 480.0,
  "complete_sets": 480.0,
  "edge": 0.03,
  "hedge_ratio": 0.96
}
```

## Pattern Analysis

### Timing Patterns
- `early_trader`: Started within 2 mins of market open
- `late_closer`: Active within 2 mins of market close
- `trades_per_minute`: Trading frequency

### Price Patterns
- `combined_buy_price`: Avg up + avg down buy price
- `bought_below_dollar`: Combined < $1.00 (arbitrage signal)
- `maker_percentage`: Proportion of maker trades

### Hedge Patterns
- `hedge_ratio`: min(up,down)/max(up,down)
- `strategy_type`: ARBITRAGE, MARKET_MAKING, DIRECTIONAL, MIXED
