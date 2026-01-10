# Bot Trading Analysis

## Goal

Analyze the trading strategies of 4 highly active bot traders on Polymarket's BTC/ETH Up/Down 15-minute markets.

**Methodology**: Verify all downloaded data against Polymarket website before analysis. No assumptions, no bias - only verified facts.

## Target Wallets

| Wallet | Polymarket Profile |
|--------|-------------------|
| `0x589222a5124a96765443b97a3498d89ffd824ad2` | [@PurpleThunderBicycleMountain](https://polymarket.com/@PurpleThunderBicycleMountain) |
| `0x0ea574f3204c5c9c0cdead90392ea0990f4d17e4` | [Direct link](https://polymarket.com/profile/0x0ea574f3204c5c9c0cdead90392ea0990f4d17e4) |
| `0xd0d6053c3c37e727402d84c14069780d360993aa` | [@k9Q2mX4L8A7ZP3R](https://polymarket.com/@k9Q2mX4L8A7ZP3R) |
| `0x63ce342161250d705dc0b16df89036c8e5f9ba9a` | [@0x8dxd](https://polymarket.com/@0x8dxd) |

## Markets Analyzed

| Slug | Question | Resolution |
|------|----------|------------|
| `eth-updown-15m-1768037400` | Ethereum Up or Down - January 10, 4:30AM-4:45AM ET | **UP** |
| `eth-updown-15m-1768036500` | Ethereum Up or Down - January 10, 4:15AM-4:30AM ET | **UP** |
| `btc-updown-15m-1768037400` | Bitcoin Up or Down - January 10, 4:30AM-4:45AM ET | **UP** |
| `btc-updown-15m-1768036500` | Bitcoin Up or Down - January 10, 4:15AM-4:30AM ET | **UP** |
| `eth-updown-15m-1768035600` | Ethereum Up or Down - January 10, 4:00AM-4:15AM ET | **DOWN** |
| `btc-updown-15m-1768034700` | Bitcoin Up or Down - January 10, 3:45AM-4:00AM ET | **UP** |

## Verification Process

1. Fetch raw trade data from Goldsky subgraph
2. Display each trade with timestamp, side, outcome, shares, price, role, tx_hash
3. User compares against Polymarket website
4. Only proceed to analysis after data is verified

## Data Source

- **Trade data**: Goldsky orderbook subgraph
- **Market metadata**: Gamma API
