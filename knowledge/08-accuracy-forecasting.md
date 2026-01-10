# Prediction Markets: Accuracy & Forecasting Analysis

## The Fundamental Question

**Do prediction markets actually work?**

The evidence suggests: **Yes, often better than alternatives.**

---

## Academic Research Summary

### Markets vs. Polls: Key Findings

| Study Finding | Implication |
|---------------|-------------|
| Markets predict elections more accurately than polls at long horizons | Better for early forecasting |
| Market prices react faster to events than poll updates | Real-time information aggregation |
| Markets were ~74% closer to final results in 1988-2004 US elections | Consistent historical performance |
| Combining markets + polls improves accuracy beyond either alone | Complementary information sources |

### Why Markets Can Outperform Polls

```
┌─────────────────────────────────────────────────────────────┐
│              PREDICTION MARKET ADVANTAGES                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. INCENTIVE ALIGNMENT                                      │
│     • Real money at stake                                    │
│     • Wrong predictions = financial loss                     │
│     • Encourages honest probability assessment               │
│                                                              │
│  2. CONTINUOUS UPDATING                                      │
│     • 24/7 price discovery                                   │
│     • Instant reaction to news                               │
│     • No polling lag time                                    │
│                                                              │
│  3. INFORMATION AGGREGATION                                  │
│     • Diverse participant perspectives                       │
│     • Private information incorporated via trading           │
│     • Wisdom of crowds effect                                │
│                                                              │
│  4. REVEALED PREFERENCE                                      │
│     • Actions speak louder than survey responses             │
│     • "Put your money where your mouth is"                   │
│     • Reduces social desirability bias                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2024 Election: A Case Study

### What Happened

| Metric | Polymarket | Polls |
|--------|------------|-------|
| Trump win probability (Nov 4) | ~62% | ~50% (toss-up) |
| Correct winner call | Yes | Mixed |
| Speed of confidence | Days before | Uncertain until end |

### Analysis

**Polymarket Advantages**:
- Incorporated "shy Trump voter" effect
- Weighted enthusiasm differentials
- Processed early voting data faster
- Integrated betting line intelligence

**Poll Limitations**:
- Response rate challenges
- Likely voter model uncertainty
- Herding around consensus
- Slow methodology updates

### Caveats

- N=1 for 2024 specifically
- Markets had access to poll data (not independent)
- Large bets can temporarily skew prices
- "Big Whale" controversy around late Trump bets

---

## Long-Term Accuracy Data

### Iowa Electronic Markets (1988-2004)

| Finding | Detail |
|---------|--------|
| Market vs. poll accuracy | Markets closer to result 74% of days |
| Horizon | Advantage larger at 100+ days out |
| Vote share prediction | Average error <2 percentage points |

### Metaculus Track Record

| Metric | All Questions | AI Questions |
|--------|---------------|--------------|
| Mean Brier Score | 0.151 | 0.207-0.230 |
| Comparison | Better than chance | Useful despite difficulty |

**Brier Score Interpretation**:
- 0 = Perfect prediction
- 0.25 = Random guessing (50/50)
- <0.25 = Better than random

### Wisdom of Crowds Effect

```
Individual Forecaster A: 60% confident
Individual Forecaster B: 40% confident
Individual Forecaster C: 70% confident
Individual Forecaster D: 50% confident
                         ─────────────
Community Average:       55% confident ← Often more accurate than any individual
```

**Why It Works**:
- Individual biases cancel out
- Different information sources aggregate
- Extreme views moderated
- Systematic errors reduce with sample size

---

## Accuracy by Market Type

### Well-Suited for Prediction Markets

| Category | Why It Works |
|----------|--------------|
| **Elections** | Binary outcome, high interest, diverse participants |
| **Sports** | Verifiable outcomes, frequent events, deep expertise |
| **Macro Events** | Economic incentives align, hedging use case |
| **Binary Questions** | Clear resolution criteria |

### Less Suited for Prediction Markets

| Category | Challenges |
|----------|------------|
| **Long-term forecasts** | Discounting, liquidity dries up |
| **Ambiguous outcomes** | Resolution disputes |
| **Niche topics** | Low liquidity, few informed traders |
| **Continuous variables** | Harder to structure as contracts |

---

## Theoretical Accuracy Framework

### Efficient Market Hypothesis Application

If prediction markets are efficient:
- Prices = best available probability estimates
- New information immediately incorporated
- Cannot systematically "beat the market"

**Reality Check**:
- Markets have frictions (fees, liquidity)
- Behavioral biases persist
- Information asymmetries exist
- Manipulation attempts occur

### Error Decomposition

```
Prediction Error = Fundamental Uncertainty + Market Inefficiency

Fundamental Uncertainty:
├── Inherent unpredictability
├── Unknown unknowns
└── Truly random elements

Market Inefficiency:
├── Thin liquidity
├── Behavioral biases
├── Manipulation
└── Information asymmetry
```

---

## Accuracy Limitations & Risks

### Manipulation Vulnerability

**Evidence**:
- Wash trading inflates volume (20-60% on Polymarket)
- Large bets can temporarily move prices
- Coordinated campaigns possible

**Impact on Accuracy**:
- Short-term distortions
- Generally self-correcting (arbitrage)
- Prices converge to fundamentals over time

### Liquidity Constraints

| Liquidity Level | Accuracy Implications |
|-----------------|----------------------|
| **High** (major elections) | Prices highly informative |
| **Medium** | Useful signal with noise |
| **Low** (niche markets) | Prices may not reflect true probability |

### Selection Bias

Markets exist for interesting questions:
- Over-representation of polarizing topics
- Under-representation of boring but important questions
- Liquidity follows attention, not importance

### Black Swan Events

- Markets cannot predict truly unprecedented events
- Prices assume historical distributions
- Tail risk systematically underestimated

---

## Combining Information Sources

### Optimal Forecasting Approach

Research suggests combining:

```
┌─────────────────────────────────────────────────────────────┐
│               COMBINED FORECASTING MODEL                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────────┐                                            │
│   │ Prediction │─────┐                                       │
│   │  Markets   │     │                                       │
│   └────────────┘     │                                       │
│                      │    ┌────────────────┐                 │
│   ┌────────────┐     ├───►│   ENSEMBLE     │                 │
│   │   Polls    │─────┤    │   FORECAST     │                 │
│   └────────────┘     │    │                │                 │
│                      │    │ More accurate  │                 │
│   ┌────────────┐     │    │ than any       │                 │
│   │ Quantitative│────┤    │ component      │                 │
│   │   Models   │     │    └────────────────┘                 │
│   └────────────┘     │                                       │
│                      │                                       │
│   ┌────────────┐     │                                       │
│   │   Expert   │─────┘                                       │
│   │  Judgment  │                                             │
│   └────────────┘                                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Why Combination Works

- Errors across methods are uncorrelated
- Each source captures different information
- Reduces reliance on any single method's assumptions
- More robust to individual method failures

---

## Benchmarking Accuracy

### Measuring Forecasting Performance

| Metric | Formula | Use Case |
|--------|---------|----------|
| **Brier Score** | Mean(prediction - outcome)² | Overall calibration |
| **Log Score** | -log(probability assigned to outcome) | Penalizes overconfidence |
| **Calibration** | Do 70% predictions happen 70% of time? | Reliability assessment |
| **Resolution** | Discrimination between outcomes | Skill measurement |

### Platform Comparisons

| Platform | Strength | Weakness |
|----------|----------|----------|
| **Polymarket** | High liquidity, real-time | Wash trading distortion |
| **Kalshi** | Regulated, US access | Lower volume historically |
| **Metaculus** | Long-term focus, no financial bias | No real money incentives |
| **Polls** | Methodological rigor | Slow updates, response bias |

---

## Key Takeaways

1. **Prediction markets generally outperform polls** at longer time horizons
2. **Real-time responsiveness** is a major advantage
3. **Wisdom of crowds** effect is empirically validated
4. **Accuracy varies** by market type, liquidity, and time horizon
5. **Manipulation is a concern** but markets tend to self-correct
6. **Best approach combines** multiple information sources
7. **Not a crystal ball** - fundamental uncertainty remains
