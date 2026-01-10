# Full Market Analysis: BTC Up/Down 5:15AM-5:30AM ET

## Market Details
- **Market**: Bitcoin Up or Down - January 9, 5:15AM-5:30AM ET
- **URL**: https://polymarket.com/event/btc-updown-15m-1767953700
- **Resolution**: UP won ($1.00), DOWN lost ($0.00)

### Token IDs
- Up: `4639165287943612223282477454395415486693001254502300426836852926573098714`
- Down: `64391555769419848323775022850371584678275525305837175168088772007000997173373`

---

## Market-Wide Statistics

| Metric | Value |
|--------|-------|
| Total unique trades | 15,353 |
| Total unique traders | 1,339 |
| Winning traders | 833 |
| Losing traders | 501 |
| Net P&L (zero-sum check) | $0.00 |

---

## Price Analysis

### Overall Averages (All Trades)

| Token | Side | Avg Price | Volume (shares) | Trades |
|-------|------|-----------|-----------------|--------|
| Up | BUY | $0.8414 | 211,783 | 6,499 |
| Up | SELL | $0.8822 | 29,616 | 1,396 |
| Down | BUY | $0.1671 | 200,576 | 6,593 |
| Down | SELL | $0.1938 | 18,349 | 865 |

### Cost Per Pair
- **Average Up + Down buy price**: $1.0085 (slightly above $1)
- **Range**: $0.9884 - $1.0152
- **Std deviation**: $0.0022

---

## VWAP Over Time

| Metric | Start | End |
|--------|-------|-----|
| Up VWAP | ~$0.55 | $0.8504 |
| Down VWAP | ~$0.45 | $0.1584 |
| Combined VWAP | ~$1.00 | $1.0088 |

The market started near 50/50 odds and moved decisively toward Up as BTC rose.

---

## Top Traders

### By Trade Count

| Rank | Address | Trades | Maker% | P&L |
|------|---------|--------|--------|-----|
| 1 | 0x4bfb...982e | 5,553 | 0% | -$5,921 |
| 2 | 0xd26a...c5ea | 1,160 | 47% | +$39 |
| 3 | 0x5892...4ad2 | 782 | 90% | +$222 |
| 4 | 0x0ea5...17e4 | 693 | 72% | +$6,445 |
| 5 | 0x6031...f96d | 626 | 78% | +$168 |

### Top Winners

| Address | P&L | Maker% | Trades |
|---------|-----|--------|--------|
| 0x0ea5...17e4 | +$6,445 | 72% | 693 |
| 0xa270...7927 | +$2,060 | 1% | 82 |
| 0x763c...76e9 | +$1,998 | 2% | 92 |
| 0x0d18...24a6 | +$1,871 | 39% | 28 |
| 0xf543...4881 | +$846 | 24% | 104 |

### Top Losers

| Address | P&L | Maker% | Trades |
|---------|-----|--------|--------|
| 0x4bfb...982e | -$5,921 | 0% | 5,553 |
| 0x6021...8ca2 | -$4,149 | 1% | 67 |
| 0x93c2...c072 | -$1,241 | 100% | 192 |
| 0xc413...7d70 | -$1,020 | 100% | 144 |
| 0x66c4...2852 | -$1,000 | 50% | 2 |

---

## Key Insights

### 1. Market Efficiency
The combined price (Up + Down) stayed remarkably close to $1.00 throughout:
- Mean: $1.0001
- Std: $0.0022
- **No significant arbitrage opportunities existed**

### 2. Biggest Loser Pattern
The biggest loser (0x4bfb...982e, -$5,921) had:
- 100% taker trades (market orders)
- Net SHORT on both sides (-120,758 Up, -65,514 Down)
- This is the market maker providing exit liquidity to everyone else

### 3. Winner Pattern
Top winner (0x0ea5...17e4, +$6,445) had:
- 72% maker trades
- Long Up (+18,082), Short Down (-1,864)
- Correctly predicted Up and got good fills via limit orders

### 4. Our Target Wallet (0x6031...f96d)
- Position P&L: +$168 (before rebates)
- Net positions: +2,730 Up, +2,271 Down (balanced)
- This confirms the maker rebate strategy works

---

## Files

- `all_market_trades.json` - 15,353 parsed trades
- `user_analysis.json` - Per-user trading statistics
- `market_price_analysis.png` - Price distribution and timeline
- `avg_price_analysis.png` - VWAP analysis over time
- `trader_analysis.png` - Top trader comparison charts
