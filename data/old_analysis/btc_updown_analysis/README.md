# BTC Up/Down Market Analysis

## Market Details
- **Market**: Bitcoin Up or Down - January 9, 6:00AM-6:15AM ET
- **URL**: https://polymarket.com/event/btc-updown-15m-1767956400
- **Resolution**: Up won ($1.00), Down lost ($0.00)
- **Total Volume**: $418,428.79

### Token IDs
- Up: `65689469986114736683609567440585706468061828613693669084008270331829703859210`
- Down: `19004630472054155562446266004006762878910712196312117007145993767241545797916`

---

## Wallet Analyzed
- **Address**: `0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d`
- **Trading Window**: 11:00:16 - 11:14:22 UTC (14.1 minutes)

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total trades | 1,232 |
| Maker trades | 989 (80.3%) |
| Taker trades | 243 (19.7%) |
| Total fees paid | $1,184.89 |
| Trading rate | 87.4 trades/min |
| Unique counterparties | 271 |

---

## Final Positions

| Outcome | Shares Bought | Shares Sold | Net Position | Avg Buy Price |
|---------|---------------|-------------|--------------|---------------|
| Up (Yes) | 6,558.58 | 1,335.22 | +5,223.36 | $0.5778 |
| Down (No) | 6,762.66 | 1,049.95 | +5,712.71 | $0.4171 |

---

## P&L Breakdown

| Component | Amount |
|-----------|--------|
| Up P&L (resolved @$1) | +$2,151.13 |
| Down P&L (resolved @$0) | -$2,321.62 |
| Fees paid | -$1,184.89 |
| **TOTAL P&L** | **-$1,355.37** |

---

## Key Finding: Cost Per Pair Analysis

**Final cost per Yes+No pair: $0.9924**

The wallet was buying Yes+No pairs for just under $1 throughout (~$0.94-$1.00 range).

**Why they lost despite being under $1:**
- Margin: ~1% ($0.99 per pair → $0.01 profit)
- Fees: ~2% (1% per leg × 2 legs)
- **Fees exceeded the arbitrage margin**

---

## Files in This Folder

### Data
- `btc_market_analysis.json` - All 1,232 parsed trades with analysis

### Charts
- `cost_per_pair.png` - **Key chart**: Cost per Yes+No pair over time
- `all_buy_shares_trendline.png` - Buy volume trendline (shares)
- `all_buy_shares_ratio.png` - Up vs Down ratio over time (shares)
- `all_buy_trendline.png` - Buy volume trendline (USDC)
- `all_buy_ratio.png` - Up vs Down ratio over time (USDC)
- `maker_buy_trendline.png` - Limit orders only trendline
- `maker_buy_ratio.png` - Limit orders only ratio
- `maker_buy_volume_trendline.png` - Limit orders cumulative + bar chart

### Scripts
- `fetch_wallet_market.py` - Script to fetch wallet trades on specific market
- `analyze_btc_market.py` - Script to analyze fetched trades

---

## Data Source
- Goldsky Subgraph API (orderbook-subgraph)
- Gamma API (market metadata)
