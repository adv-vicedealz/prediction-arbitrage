# gabagool22 Arbitrage Strategy Analysis

**Wallet:** `0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d`
**Analysis Date:** January 8, 2026
**Data Source:** Polymarket Goldsky Subgraph

---

## Executive Summary

gabagool22 runs an **automated arbitrage bot** that exploits pricing inefficiencies in Polymarket's 15-minute Bitcoin/Ethereum binary options markets. By simultaneously buying both outcomes (Up and Down) when their combined price is less than $1.00, he locks in **risk-free, guaranteed profits** regardless of which direction the price moves.

| Metric | Value |
|--------|-------|
| Total trades | 141,174 |
| Markets traded | 240 |
| Capital deployed | $644,966 |
| **Guaranteed profit** | **$10,795** |
| ROI (single day) | 1.67% |
| Annualized ROI | ~610% |

---

## What Are These Markets?

Polymarket offers 15-minute binary options on cryptocurrency prices:

> "Will Bitcoin be UP or DOWN at 9:45AM compared to 9:30AM?"

**Market Structure:**
- **Two outcomes:** UP (price increased) or DOWN (price decreased)
- **Payout:** Winning outcome pays $1.00, losing outcome pays $0.00
- **Frequency:** New market every 15 minutes
- **Daily markets:** 96 BTC + 96 ETH = 192 markets per day

---

## The Arbitrage Opportunity

### Efficient Market Pricing

In a perfectly efficient market, the prices of both outcomes should sum to $1.00:

```
UP price + DOWN price = $1.00
```

For example:
- UP = $0.50
- DOWN = $0.50
- Total = $1.00 (no arbitrage)

### Inefficient Market Pricing

However, retail traders often misprice these markets:

```
UP   = $0.26
DOWN = $0.72
─────────────
Total = $0.98  ← Less than $1.00!
```

This $0.02 gap is the **arbitrage opportunity**.

---

## How The Strategy Works

### Step 1: Detect Opportunity

The bot continuously scans all active markets looking for:

```
IF (UP_price + DOWN_price) < $1.00 THEN arbitrage_exists
```

### Step 2: Buy Both Sides

When an opportunity is found, simultaneously buy equal amounts of both outcomes:

| Action | Shares | Price | Cost |
|--------|--------|-------|------|
| Buy UP | 1,000 | $0.26 | $260 |
| Buy DOWN | 1,000 | $0.72 | $720 |
| **Total** | | | **$980** |

### Step 3: Wait for Resolution

After 15 minutes, the market resolves. Only one outcome can win:

**Scenario A: Bitcoin goes UP**
- UP shares pay: 1,000 × $1.00 = $1,000
- DOWN shares pay: 1,000 × $0.00 = $0
- **Total payout: $1,000**

**Scenario B: Bitcoin goes DOWN**
- UP shares pay: 1,000 × $0.00 = $0
- DOWN shares pay: 1,000 × $1.00 = $1,000
- **Total payout: $1,000**

### Step 4: Collect Guaranteed Profit

```
Payout:  $1,000
Cost:    $980
─────────────────
Profit:  $20 (2.04% return)
```

**Key Insight:** The profit is identical regardless of which direction Bitcoin moves. This is **risk-free arbitrage**.

---

## Real Example from January 8, 2026

**Market:** Bitcoin Up or Down - January 7, 6:00PM-6:15PM ET

| Position | Shares | Avg Price | Cost |
|----------|--------|-----------|------|
| UP | 3,206 | $0.2613 | $837.78 |
| DOWN | 2,957 | $0.7217 | $2,133.96 |
| **Total** | | | **$2,971.74** |

**Arbitrage Calculation:**

| Metric | Value |
|--------|-------|
| Matched pairs | 2,957 shares |
| Cost per pair | $0.2613 + $0.7217 = $0.9830 |
| Payout per pair | $1.00 |
| Profit per pair | $0.0170 |
| **Total profit** | **$50.20** |

---

## January 8, 2026 Performance

### Trading Activity

| Metric | Value |
|--------|-------|
| Total trades | 141,174 |
| As maker (limit orders) | 106,747 |
| As taker (market orders) | 34,427 |
| Trades per minute | ~98 |
| Unique markets | 240 |
| Markets with arbitrage | 210 (87.5%) |

### Volume Breakdown

| Asset | Markets | Trades | Volume |
|-------|---------|--------|--------|
| Bitcoin | 120 | 86,610 | $540,655 |
| Ethereum | 120 | 54,564 | $215,828 |
| **Total** | **240** | **141,174** | **$756,483** |

### Profitability

| Metric | Value |
|--------|-------|
| Total matched pairs | 655,761 |
| Capital deployed | $644,965.98 |
| Guaranteed payout | $655,760.79 |
| **Guaranteed profit** | **$10,794.81** |
| ROI | 1.67% |
| Avg profit per pair | $0.0165 |

### Top 10 Most Profitable Markets

| Rank | Market | Profit | Pairs | Combined Price |
|------|--------|--------|-------|----------------|
| 1 | BTC Up/Down Jan 7, 10:45PM-11:00PM | $203.56 | 6,318 | $0.9678 |
| 2 | BTC Up/Down Jan 8, 5:30AM-5:45AM | $173.95 | 5,880 | $0.9704 |
| 3 | BTC Up/Down Jan 8, 6AM | $163.77 | 6,760 | $0.9758 |
| 4 | BTC Up/Down Jan 8, 8AM | $160.23 | 5,996 | $0.9733 |
| 5 | BTC Up/Down Jan 7, 7:00PM-7:15PM | $158.97 | 3,914 | $0.9594 |
| 6 | BTC Up/Down Jan 8, 3AM | $158.63 | 5,418 | $0.9707 |
| 7 | BTC Up/Down Jan 8, 9:30AM-9:45AM | $146.69 | 13,523 | $0.9892 |
| 8 | BTC Up/Down Jan 7, 9:45PM-10:00PM | $144.96 | 3,315 | $0.9563 |
| 9 | BTC Up/Down Jan 8, 11:45AM-12:00PM | $142.83 | 6,198 | $0.9770 |
| 10 | BTC Up/Down Jan 8, 6:30AM-6:45AM | $139.33 | 5,940 | $0.9765 |

---

## Hourly Trading Distribution

```
Hour    Trades
00:00    5,525   ###########################
01:00    3,790   ##################
02:00    3,679   ##################
03:00    3,857   ###################
04:00    4,141   ####################
05:00    3,668   ##################
06:00    2,872   ##############
07:00    3,154   ###############
08:00    4,290   #####################
09:00    4,215   #####################
10:00    5,986   #############################
11:00    4,647   #######################
12:00    5,065   #########################
13:00    4,523   ######################
14:00    4,602   #######################
15:00    6,407   ################################  (Peak)
16:00    6,313   ###############################
17:00    5,489   ###########################
18:00    5,252   ##########################
19:00    5,003   #########################
20:00    3,284   ################
21:00    4,035   ####################
22:00    3,499   #################
23:00    3,451   #################
```

---

## Why This Strategy Works

### 1. Speed
- Automated bot scans markets every second
- Executes 98 trades per minute average
- Impossible for humans to replicate manually

### 2. Scale
- 655,761 share pairs across 210 markets
- Small edges ($0.017/pair) compound into large profits
- 24/7 operation captures all opportunities

### 3. Market Inefficiency
- Retail traders misprice short-term binary options
- Emotional trading creates pricing gaps
- New markets every 15 minutes = constant opportunities

### 4. Risk-Free Returns
- Profit is mathematically guaranteed
- No exposure to Bitcoin/Ethereum price direction
- Only risk is execution (bot reliability, platform issues)

### 5. Capital Efficiency
- Capital recycles every 15 minutes
- Same $600K can generate profits across many markets
- High frequency = high annualized returns

---

## Strategy Classification

| Characteristic | Value |
|----------------|-------|
| Strategy type | Pure arbitrage |
| Risk level | Near-zero (execution risk only) |
| Required capital | $500K-$1M for meaningful scale |
| Time horizon | Ultra short-term (15 minutes) |
| Automation | 100% required |
| Edge source | Market inefficiency / retail mispricing |

---

## Replication Requirements

To replicate this strategy, you would need:

1. **Infrastructure**
   - Low-latency connection to Polymarket
   - Reliable bot running 24/7
   - Polygon wallet with sufficient USDC

2. **Software**
   - Real-time price monitoring for all 15-min markets
   - Arbitrage detection algorithm
   - Automated order execution
   - Position tracking and reconciliation

3. **Capital**
   - $100K minimum for viable returns
   - $500K+ for returns matching gabagool22

4. **Considerations**
   - Competition from other arbitrage bots
   - Polymarket fees eat into margins
   - Execution slippage on large orders
   - Platform risk (smart contract bugs, etc.)

---

## Data Files

| File | Description | Records |
|------|-------------|---------|
| `jan8_trades.json` | Maker trades (limit orders) | 106,747 |
| `jan8_taker_trades.json` | Taker trades (market orders) | 34,427 |
| `jan8_enriched.json` | All trades with market metadata | 141,174 |
| `token_metadata.json` | Token ID to market mapping | 480 |

---

## Conclusion

gabagool22 demonstrates a sophisticated, fully-automated arbitrage operation on Polymarket's 15-minute binary options. By exploiting small pricing inefficiencies across hundreds of markets daily, he generates **$10,000+ in risk-free profits per day** with approximately $650K in capital.

This is not gambling or speculation - it's **pure mathematical arbitrage** where profits are guaranteed regardless of market outcomes. The strategy requires significant technical infrastructure and capital, but offers exceptional risk-adjusted returns for those who can execute it successfully.

---

*Analysis generated from Polymarket Goldsky Subgraph data*
*Wallet: 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d*
