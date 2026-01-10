# How to Replicate gabagool22's Arbitrage Strategy

A complete guide to building an automated arbitrage bot for Polymarket's 15-minute binary options.

---

## Table of Contents

1. [Strategy Overview](#strategy-overview)
2. [Requirements](#requirements)
3. [Step 1: Find Active Markets](#step-1-find-active-markets)
4. [Step 2: Get Real-Time Prices](#step-2-get-real-time-prices)
5. [Step 3: Detect Arbitrage Opportunities](#step-3-detect-arbitrage-opportunities)
6. [Step 4: Execute Trades](#step-4-execute-trades)
7. [Step 5: Redeem Winnings](#step-5-redeem-winnings)
8. [Complete Bot Implementation](#complete-bot-implementation)
9. [Capital & Profitability](#capital--profitability)
10. [Risks & Considerations](#risks--considerations)

---

## Strategy Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  1. SCAN    │ ──▶ │  2. DETECT  │ ──▶ │  3. EXECUTE │ ──▶ │  4. COLLECT │
│  Markets    │     │  Arbitrage  │     │  Trades     │     │  Payout     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
 Monitor all         Find where          Buy BOTH           Wait for
 15-min BTC/ETH      UP + DOWN           UP and DOWN        resolution
 markets in          < $1.00             simultaneously     & redeem
 real-time
```

### The Math

```
If: UP_price + DOWN_price < $1.00
Then: Buy both → Guaranteed profit = $1.00 - (UP + DOWN)

Example:
  UP   = $0.45
  DOWN = $0.52
  ─────────────
  Cost = $0.97

  Payout = $1.00 (always, regardless of outcome)
  Profit = $0.03 per share pair (3.1% return)
```

---

## Requirements

### Technical

| Component | Requirement |
|-----------|-------------|
| Language | Python 3.9+ |
| Network | Low latency connection |
| Wallet | Polygon wallet with private key |
| Capital | USDC on Polygon |

### Dependencies

```bash
pip install web3 requests python-dotenv py-clob-client
```

### Polymarket API Access

1. **CLOB API** - For placing orders
2. **Gamma API** - For market discovery
3. **WebSocket** - For real-time prices (optional but recommended)

### Wallet Setup

```python
# .env file
PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=0xYourWalletAddress
```

---

## Step 1: Find Active Markets

### Discover 15-Minute Markets

```python
import requests
from datetime import datetime, timedelta

GAMMA_API = "https://gamma-api.polymarket.com"

def get_active_15min_markets():
    """
    Find all active BTC/ETH 15-minute Up/Down markets.
    These markets resolve every 15 minutes.
    """
    markets = []

    # Search for Bitcoin markets
    resp = requests.get(
        f"{GAMMA_API}/markets",
        params={
            "closed": False,
            "limit": 100,
            "order": "endDate",
            "ascending": True
        }
    )

    all_markets = resp.json()

    for market in all_markets:
        question = market.get("question", "")

        # Filter for 15-minute Up/Down markets
        if ("Up or Down" in question and
            ("Bitcoin" in question or "Ethereum" in question)):

            # Parse end date
            end_date = market.get("endDate")
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

                # Only include markets ending within next 2 hours
                if end_dt < datetime.now(end_dt.tzinfo) + timedelta(hours=2):
                    markets.append({
                        "conditionId": market.get("conditionId"),
                        "question": question,
                        "slug": market.get("slug"),
                        "endDate": end_date,
                        "outcomes": market.get("outcomes"),
                        "clobTokenIds": market.get("clobTokenIds")
                    })

    return markets


# Example usage
if __name__ == "__main__":
    markets = get_active_15min_markets()
    print(f"Found {len(markets)} active 15-min markets")
    for m in markets[:5]:
        print(f"  - {m['question']}")
```

---

## Step 2: Get Real-Time Prices

### Option A: REST API (Simple)

```python
CLOB_API = "https://clob.polymarket.com"

def get_prices(token_id: str) -> dict:
    """
    Get current bid/ask/mid prices for a token.
    """
    try:
        # Get orderbook
        resp = requests.get(
            f"{CLOB_API}/book",
            params={"token_id": token_id}
        )
        book = resp.json()

        # Best bid and ask
        bids = book.get("bids", [])
        asks = book.get("asks", [])

        best_bid = float(bids[0]["price"]) if bids else 0
        best_ask = float(asks[0]["price"]) if asks else 1

        # Available liquidity
        bid_size = float(bids[0]["size"]) if bids else 0
        ask_size = float(asks[0]["size"]) if asks else 0

        return {
            "bid": best_bid,
            "ask": best_ask,
            "mid": (best_bid + best_ask) / 2,
            "bid_size": bid_size,
            "ask_size": ask_size
        }
    except Exception as e:
        print(f"Error getting prices: {e}")
        return None


def get_market_prices(market: dict) -> dict:
    """
    Get prices for both outcomes (UP and DOWN) of a market.
    """
    token_ids = market.get("clobTokenIds", [])
    outcomes = market.get("outcomes", ["Up", "Down"])

    if len(token_ids) < 2:
        return None

    up_prices = get_prices(token_ids[0])
    down_prices = get_prices(token_ids[1])

    if not up_prices or not down_prices:
        return None

    return {
        "market": market["question"],
        "up": {
            "token_id": token_ids[0],
            "outcome": outcomes[0],
            **up_prices
        },
        "down": {
            "token_id": token_ids[1],
            "outcome": outcomes[1],
            **down_prices
        }
    }
```

### Option B: WebSocket (Faster, Recommended for Production)

```python
import asyncio
import websockets
import json

WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

async def subscribe_to_prices(token_ids: list, callback):
    """
    Subscribe to real-time price updates via WebSocket.
    """
    async with websockets.connect(WS_URL) as ws:
        # Subscribe to each token
        for token_id in token_ids:
            subscribe_msg = {
                "type": "subscribe",
                "channel": "market",
                "assets_ids": [token_id]
            }
            await ws.send(json.dumps(subscribe_msg))

        # Listen for updates
        async for message in ws:
            data = json.loads(message)
            await callback(data)


async def price_callback(data):
    """Handle incoming price updates."""
    print(f"Price update: {data}")
```

---

## Step 3: Detect Arbitrage Opportunities

```python
def detect_arbitrage(market_prices: dict, min_profit_pct: float = 0.5) -> dict:
    """
    Check if arbitrage opportunity exists.

    Args:
        market_prices: Prices for UP and DOWN outcomes
        min_profit_pct: Minimum profit percentage to consider (default 0.5%)

    Returns:
        Arbitrage opportunity details or None
    """
    up = market_prices["up"]
    down = market_prices["down"]

    # Cost to buy both sides (use ask prices - what we pay)
    up_cost = up["ask"]
    down_cost = down["ask"]
    combined_cost = up_cost + down_cost

    # Guaranteed payout is always $1.00
    payout = 1.0

    # Profit calculation
    profit_per_pair = payout - combined_cost
    profit_pct = (profit_per_pair / combined_cost) * 100 if combined_cost > 0 else 0

    # Check if profitable
    if profit_pct >= min_profit_pct:
        # Calculate max size based on available liquidity
        max_pairs = min(up["ask_size"], down["ask_size"])
        max_profit = profit_per_pair * max_pairs

        return {
            "market": market_prices["market"],
            "profitable": True,
            "up_token": up["token_id"],
            "down_token": down["token_id"],
            "up_price": up_cost,
            "down_price": down_cost,
            "combined_cost": combined_cost,
            "profit_per_pair": profit_per_pair,
            "profit_pct": profit_pct,
            "max_pairs": max_pairs,
            "max_profit": max_profit
        }

    return {
        "market": market_prices["market"],
        "profitable": False,
        "combined_cost": combined_cost,
        "profit_pct": profit_pct
    }


# Example: Scan all markets for arbitrage
def scan_for_arbitrage(markets: list, min_profit_pct: float = 0.5) -> list:
    """
    Scan all markets and return arbitrage opportunities.
    """
    opportunities = []

    for market in markets:
        prices = get_market_prices(market)
        if prices:
            arb = detect_arbitrage(prices, min_profit_pct)
            if arb.get("profitable"):
                opportunities.append(arb)
                print(f"✓ ARBITRAGE FOUND: {arb['market'][:50]}")
                print(f"  UP: ${arb['up_price']:.4f} + DOWN: ${arb['down_price']:.4f} = ${arb['combined_cost']:.4f}")
                print(f"  Profit: ${arb['profit_per_pair']:.4f} ({arb['profit_pct']:.2f}%)")
                print(f"  Max pairs: {arb['max_pairs']:.0f} = ${arb['max_profit']:.2f} potential")
                print()

    return opportunities
```

---

## Step 4: Execute Trades

### Setup Polymarket Client

```python
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize client
def get_clob_client():
    """
    Initialize authenticated CLOB client.
    """
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("PRIVATE_KEY"),
        chain_id=137,  # Polygon mainnet
        signature_type=2,  # POLY_GNOSIS_SAFE
    )

    # Derive API credentials
    client.set_api_creds(client.create_or_derive_api_creds())

    return client
```

### Place Orders

```python
def execute_arbitrage(client: ClobClient, opportunity: dict, size: float) -> dict:
    """
    Execute arbitrage by buying both UP and DOWN outcomes.

    Args:
        client: Authenticated CLOB client
        opportunity: Arbitrage opportunity from detect_arbitrage()
        size: Number of share pairs to buy

    Returns:
        Execution results
    """
    results = {"success": False, "orders": []}

    try:
        # Order 1: Buy UP shares
        up_order = OrderArgs(
            token_id=opportunity["up_token"],
            price=opportunity["up_price"],
            size=size,
            side="BUY",
            order_type=OrderType.GTC  # Good til cancelled
        )

        up_result = client.create_and_post_order(up_order)
        results["orders"].append({
            "side": "UP",
            "order_id": up_result.get("orderID"),
            "status": up_result.get("status")
        })
        print(f"  UP order placed: {up_result}")

        # Order 2: Buy DOWN shares
        down_order = OrderArgs(
            token_id=opportunity["down_token"],
            price=opportunity["down_price"],
            size=size,
            side="BUY",
            order_type=OrderType.GTC
        )

        down_result = client.create_and_post_order(down_order)
        results["orders"].append({
            "side": "DOWN",
            "order_id": down_result.get("orderID"),
            "status": down_result.get("status")
        })
        print(f"  DOWN order placed: {down_result}")

        results["success"] = True
        results["size"] = size
        results["expected_cost"] = opportunity["combined_cost"] * size
        results["expected_profit"] = opportunity["profit_per_pair"] * size

    except Exception as e:
        print(f"  Error executing arbitrage: {e}")
        results["error"] = str(e)

    return results
```

### Market Orders (Faster Execution)

```python
def execute_market_orders(client: ClobClient, opportunity: dict, size: float) -> dict:
    """
    Execute with market orders for faster fills (at worse prices).
    Use when speed is more important than price.
    """
    results = {"success": False, "orders": []}

    try:
        # Market buy UP
        up_order = OrderArgs(
            token_id=opportunity["up_token"],
            price=0.99,  # Max price willing to pay
            size=size,
            side="BUY",
            order_type=OrderType.FOK  # Fill or Kill
        )
        up_result = client.create_and_post_order(up_order)
        results["orders"].append({"side": "UP", **up_result})

        # Market buy DOWN
        down_order = OrderArgs(
            token_id=opportunity["down_token"],
            price=0.99,
            size=size,
            side="BUY",
            order_type=OrderType.FOK
        )
        down_result = client.create_and_post_order(down_order)
        results["orders"].append({"side": "DOWN", **down_result})

        results["success"] = True

    except Exception as e:
        results["error"] = str(e)

    return results
```

---

## Step 5: Redeem Winnings

After the market resolves, one outcome wins and pays $1.00.

### Check Resolution

```python
def check_market_resolved(condition_id: str) -> dict:
    """
    Check if a market has resolved and get the winning outcome.
    """
    resp = requests.get(
        f"{GAMMA_API}/markets",
        params={"condition_id": condition_id}
    )

    markets = resp.json()
    if not markets:
        return {"resolved": False}

    market = markets[0]

    return {
        "resolved": market.get("closed", False),
        "winning_outcome": market.get("winningOutcome"),
        "resolution_time": market.get("resolutionTime")
    }
```

### Redeem Shares

```python
from web3 import Web3

# Contract addresses
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEG_RISK_CTF = "0xC5d563A36AE78145C45a50134d48A1215220f80a"

def redeem_positions(client: ClobClient, condition_id: str):
    """
    Redeem winning shares after market resolution.
    The winning outcome pays $1.00 per share.
    """
    # This is handled automatically by Polymarket in most cases
    # Winnings are credited to your USDC balance

    # Check your balance
    balance = client.get_balance()
    print(f"Current USDC balance: ${balance}")

    # For manual redemption, you'd interact with the CTF contract
    # But Polymarket typically handles this automatically
```

---

## Complete Bot Implementation

### Main Bot Loop

```python
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArbitrageBot")

class ArbitrageBot:
    def __init__(self, min_profit_pct: float = 0.5, max_position_size: float = 1000):
        self.client = get_clob_client()
        self.min_profit_pct = min_profit_pct
        self.max_position_size = max_position_size
        self.active_positions = {}

    def run(self):
        """Main bot loop."""
        logger.info("Starting Arbitrage Bot...")
        logger.info(f"Min profit: {self.min_profit_pct}%")
        logger.info(f"Max position: ${self.max_position_size}")

        while True:
            try:
                self.scan_and_execute()
                time.sleep(1)  # Scan every second

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)

    def scan_and_execute(self):
        """Single scan iteration."""
        # Get active markets
        markets = get_active_15min_markets()
        logger.debug(f"Scanning {len(markets)} markets...")

        for market in markets:
            # Skip if we already have a position
            if market["conditionId"] in self.active_positions:
                continue

            # Get prices
            prices = get_market_prices(market)
            if not prices:
                continue

            # Check for arbitrage
            arb = detect_arbitrage(prices, self.min_profit_pct)

            if arb.get("profitable"):
                logger.info(f"🎯 Arbitrage found: {arb['market'][:50]}")
                logger.info(f"   Profit: {arb['profit_pct']:.2f}%")

                # Calculate position size
                size = min(
                    arb["max_pairs"],
                    self.max_position_size / arb["combined_cost"]
                )

                if size >= 10:  # Minimum 10 shares
                    # Execute
                    result = execute_arbitrage(self.client, arb, size)

                    if result["success"]:
                        logger.info(f"   ✓ Executed {size:.0f} pairs")
                        logger.info(f"   Expected profit: ${result['expected_profit']:.2f}")

                        # Track position
                        self.active_positions[market["conditionId"]] = {
                            "size": size,
                            "cost": result["expected_cost"],
                            "expected_profit": result["expected_profit"],
                            "timestamp": datetime.now()
                        }
                    else:
                        logger.warning(f"   ✗ Execution failed: {result.get('error')}")


# Run the bot
if __name__ == "__main__":
    bot = ArbitrageBot(
        min_profit_pct=0.5,      # Minimum 0.5% profit
        max_position_size=5000   # Max $5000 per market
    )
    bot.run()
```

### Configuration File

```python
# config.py

# API Endpoints
CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# Trading Parameters
MIN_PROFIT_PCT = 0.5          # Minimum profit to execute (0.5%)
MAX_POSITION_SIZE = 5000      # Max USD per market
MIN_SHARES = 10               # Minimum shares to trade
SCAN_INTERVAL = 1             # Seconds between scans

# Risk Management
MAX_TOTAL_EXPOSURE = 50000    # Max total capital at risk
MAX_POSITIONS = 20            # Max simultaneous positions
SLIPPAGE_BUFFER = 0.002       # 0.2% buffer for slippage

# Polygon Network
CHAIN_ID = 137
RPC_URL = "https://polygon-rpc.com"
```

---

## Capital & Profitability

### Expected Returns

Based on gabagool22's January 8th performance:

| Capital | Daily Profit | Monthly | Annual |
|---------|--------------|---------|--------|
| $100K | ~$1,700 | ~$51K | ~$620K |
| $500K | ~$8,500 | ~$255K | ~$3.1M |
| $1M | ~$17,000 | ~$510K | ~$6.2M |

### Assumptions

- 1.67% daily ROI (gabagool22's actual)
- 24/7 operation
- Consistent market inefficiency
- No major execution issues

### Reality Check

- Competition reduces opportunities over time
- Fees eat into profits (~0.1-0.2%)
- Execution slippage on larger orders
- Some markets have thin liquidity
- Platform risk (smart contract bugs, downtime)

---

## Risks & Considerations

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Bot downtime | Redundant servers, monitoring |
| API rate limits | Respect limits, use WebSockets |
| Execution failure | Retry logic, partial fill handling |
| Network issues | Multiple RPC endpoints |

### Market Risks

| Risk | Mitigation |
|------|------------|
| Thin liquidity | Size limits per market |
| Price slippage | Use limit orders, slippage buffer |
| Competition | Faster execution, better prices |
| Market changes | Monitor for rule changes |

### Financial Risks

| Risk | Mitigation |
|------|------------|
| Smart contract bug | Limit exposure, diversify |
| Platform insolvency | Don't keep all funds on platform |
| Regulatory action | Stay informed, have exit plan |

### Execution Risks

```
CRITICAL: Partial Fills

If you buy UP but fail to buy DOWN, you have DIRECTIONAL EXPOSURE!

Example:
  - Buy 1000 UP @ $0.45 = $450 ✓
  - Buy 1000 DOWN @ $0.52 = FAILED ✗

  Now you're betting $450 that Bitcoin goes UP.
  If it goes DOWN, you lose $450!

SOLUTION: Use atomic execution or immediately unwind failed legs.
```

---

## Legal Considerations

1. **Jurisdiction** - Polymarket may not be legal in your country (US restricted)
2. **Taxes** - Profits are likely taxable income
3. **Reporting** - Large volumes may trigger reporting requirements
4. **Terms of Service** - Ensure bot trading is allowed

---

## Summary

### To replicate gabagool22's strategy:

1. **Setup**: Wallet + USDC on Polygon + API access
2. **Scan**: Monitor all 15-min BTC/ETH markets
3. **Detect**: Find where UP + DOWN < $1.00
4. **Execute**: Buy both sides simultaneously
5. **Collect**: Wait 15 min, receive $1.00 payout

### Key Success Factors

- **Speed**: Sub-second detection and execution
- **Scale**: Trade hundreds of markets daily
- **Reliability**: 24/7 uptime with error handling
- **Capital**: $100K+ for meaningful returns

### Expected Results

- ~1.5-2% daily ROI
- ~$10K/day profit on $650K capital
- Risk-free (if executed correctly)

---

*This guide is for educational purposes. Trading involves risk. Do your own research.*
