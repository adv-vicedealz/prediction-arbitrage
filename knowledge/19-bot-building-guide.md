# Prediction Markets: Practical Bot Building Guide

## Prerequisites

### Technical Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.9+ | 3.11+ |
| RAM | 4GB | 8GB+ |
| Network | Stable broadband | Low-latency VPS |
| Storage | 10GB | 50GB (for historical data) |

### Knowledge Requirements

- Python programming (intermediate)
- API integration basics
- Basic blockchain/Web3 concepts
- Understanding of order books and trading

### Capital Requirements

| Strategy | Minimum | Recommended |
|----------|---------|-------------|
| Learning/Testing | $100 | $500 |
| Simple arbitrage | $1,000 | $5,000 |
| Market making | $5,000 | $10,000+ |
| Multi-platform | $10,000 | $25,000+ |

---

## Environment Setup

### Step 1: Project Structure

```bash
mkdir polymarket-bot
cd polymarket-bot

# Create structure
mkdir -p src/{strategies,utils,data}
mkdir -p config
mkdir -p logs
mkdir -p tests

# Initialize
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### Step 2: Install Dependencies

```bash
# requirements.txt
cat > requirements.txt << 'EOF'
py-clob-client==0.29.0
web3==6.14.0
python-dotenv==1.0.0
requests==2.31.0
websockets==12.0
pandas==2.1.0
numpy==1.26.0
aiohttp==3.9.0
schedule==1.2.0
loguru==0.7.2
EOF

pip install -r requirements.txt
```

### Step 3: Configuration

```bash
# .env file
cat > .env << 'EOF'
# Polymarket
PRIVATE_KEY=your_wallet_private_key_here
POLY_API_KEY=your_api_key
POLY_API_SECRET=your_api_secret
POLY_API_PASSPHRASE=optional_passphrase

# Kalshi (optional)
KALSHI_API_KEY_ID=your_kalshi_key_id
KALSHI_PRIVATE_KEY_PATH=./kalshi_private_key.pem

# Settings
LOG_LEVEL=INFO
DRY_RUN=true
EOF
```

### Step 4: Wallet Setup

```python
# src/utils/wallet.py
from eth_account import Account
from dotenv import load_dotenv
import os

load_dotenv()

def get_wallet():
    """Load wallet from private key"""
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise ValueError("PRIVATE_KEY not found in .env")

    account = Account.from_key(private_key)
    print(f"Wallet loaded: {account.address}")
    return account

def get_address():
    return get_wallet().address
```

---

## Step-by-Step: First Trading Bot

### 1. Basic Client Setup

```python
# src/client.py
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from dotenv import load_dotenv
import os

load_dotenv()

class PolymarketClient:
    HOST = "https://clob.polymarket.com"
    CHAIN_ID = 137

    def __init__(self):
        self.private_key = os.getenv("PRIVATE_KEY")
        self.client = None
        self._setup_client()

    def _setup_client(self):
        """Initialize authenticated client"""
        # Check if we have API creds
        api_key = os.getenv("POLY_API_KEY")

        if api_key:
            # Use existing creds
            creds = ApiCreds(
                api_key=api_key,
                api_secret=os.getenv("POLY_API_SECRET"),
                api_passphrase=os.getenv("POLY_API_PASSPHRASE", "")
            )
            self.client = ClobClient(
                host=self.HOST,
                chain_id=self.CHAIN_ID,
                key=self.private_key,
                creds=creds,
                signature_type=0
            )
        else:
            # Create new creds
            temp_client = ClobClient(
                host=self.HOST,
                chain_id=self.CHAIN_ID,
                key=self.private_key
            )
            creds = temp_client.create_api_creds()
            print(f"New API credentials created:")
            print(f"  API Key: {creds.api_key}")
            print(f"  API Secret: {creds.api_secret}")
            print(f"  Passphrase: {creds.api_passphrase}")
            print("Add these to your .env file!")

            self.client = ClobClient(
                host=self.HOST,
                chain_id=self.CHAIN_ID,
                key=self.private_key,
                creds=creds,
                signature_type=0
            )

    def get_markets(self):
        return self.client.get_markets()

    def get_order_book(self, token_id):
        return self.client.get_order_book(token_id)

    def get_midpoint(self, token_id):
        return self.client.get_midpoint(token_id)

    def get_positions(self):
        return self.client.get_positions()

    def place_order(self, token_id, price, size, side):
        order = self.client.create_order(
            token_id=token_id,
            price=price,
            size=size,
            side=side
        )
        return self.client.post_order(order)

    def cancel_order(self, order_id):
        return self.client.cancel_order(order_id)

    def cancel_all(self):
        return self.client.cancel_all()
```

### 2. Market Data Fetcher

```python
# src/data/markets.py
import requests
from typing import List, Dict, Optional

class GammaAPI:
    BASE_URL = "https://gamma-api.polymarket.com"

    def get_markets(self, active: bool = True, limit: int = 100) -> List[Dict]:
        """Fetch markets from Gamma API"""
        params = {
            "active": str(active).lower(),
            "limit": limit
        }
        response = requests.get(f"{self.BASE_URL}/markets", params=params)
        response.raise_for_status()
        return response.json()

    def get_market_by_id(self, market_id: str) -> Optional[Dict]:
        """Get single market by ID"""
        response = requests.get(f"{self.BASE_URL}/markets", params={"id": market_id})
        response.raise_for_status()
        markets = response.json()
        return markets[0] if markets else None

    def get_market_by_slug(self, slug: str) -> Optional[Dict]:
        """Get market by URL slug"""
        response = requests.get(f"{self.BASE_URL}/markets", params={"slug": slug})
        response.raise_for_status()
        markets = response.json()
        return markets[0] if markets else None

    def search_markets(self, query: str) -> List[Dict]:
        """Search markets by question text"""
        all_markets = self.get_markets(limit=500)
        query_lower = query.lower()
        return [m for m in all_markets if query_lower in m.get('question', '').lower()]
```

### 3. Simple Arbitrage Detector

```python
# src/strategies/arbitrage.py
from dataclasses import dataclass
from typing import List, Optional
import time

@dataclass
class ArbitrageOpportunity:
    market_id: str
    question: str
    yes_price: float
    no_price: float
    combined: float
    profit_potential: float
    token_ids: tuple

class ArbitrageDetector:
    def __init__(self, client, gamma_api, min_profit: float = 0.02):
        self.client = client
        self.gamma = gamma_api
        self.min_profit = min_profit  # 2% minimum

    def scan_single_market_arb(self) -> List[ArbitrageOpportunity]:
        """Find YES + NO < $1.00 opportunities"""
        opportunities = []
        markets = self.gamma.get_markets(active=True, limit=200)

        for market in markets:
            try:
                prices = market.get('outcomePrices', [])
                if len(prices) != 2:
                    continue

                yes_price = float(prices[0])
                no_price = float(prices[1])
                combined = yes_price + no_price

                # Arbitrage exists if combined < 1.00
                if combined < (1.0 - self.min_profit):
                    profit = 1.0 - combined
                    token_ids = tuple(market.get('clob_token_ids', []))

                    opp = ArbitrageOpportunity(
                        market_id=market['id'],
                        question=market['question'][:50],
                        yes_price=yes_price,
                        no_price=no_price,
                        combined=combined,
                        profit_potential=profit,
                        token_ids=token_ids
                    )
                    opportunities.append(opp)

            except Exception as e:
                continue

        return sorted(opportunities, key=lambda x: x.profit_potential, reverse=True)

    def execute_arb(self, opp: ArbitrageOpportunity, amount: float = 100):
        """Execute single-market arbitrage"""
        if len(opp.token_ids) != 2:
            raise ValueError("Invalid token IDs")

        yes_token, no_token = opp.token_ids

        # Buy YES
        yes_order = self.client.place_order(
            token_id=yes_token,
            price=opp.yes_price + 0.01,  # Slight premium for fill
            size=amount,
            side="BUY"
        )

        # Buy NO
        no_order = self.client.place_order(
            token_id=no_token,
            price=opp.no_price + 0.01,
            size=amount,
            side="BUY"
        )

        return {
            'yes_order': yes_order,
            'no_order': no_order,
            'expected_profit': opp.profit_potential * amount
        }
```

### 4. Main Bot Runner

```python
# src/main.py
from client import PolymarketClient
from data.markets import GammaAPI
from strategies.arbitrage import ArbitrageDetector
from loguru import logger
import time
import os

def main():
    # Setup logging
    logger.add("logs/bot_{time}.log", rotation="1 day")

    # Initialize
    logger.info("Initializing bot...")
    client = PolymarketClient()
    gamma = GammaAPI()
    detector = ArbitrageDetector(client, gamma, min_profit=0.02)

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    logger.info(f"Dry run mode: {dry_run}")

    # Main loop
    logger.info("Starting arbitrage scanner...")
    while True:
        try:
            # Scan for opportunities
            opportunities = detector.scan_single_market_arb()

            if opportunities:
                logger.info(f"Found {len(opportunities)} opportunities")
                for opp in opportunities[:5]:  # Top 5
                    logger.info(
                        f"  {opp.question}: "
                        f"YES={opp.yes_price:.3f} + NO={opp.no_price:.3f} = "
                        f"{opp.combined:.3f} (profit: {opp.profit_potential:.1%})"
                    )

                    if not dry_run and opp.profit_potential > 0.03:
                        logger.info(f"Executing trade...")
                        result = detector.execute_arb(opp, amount=50)
                        logger.info(f"Result: {result}")

            else:
                logger.debug("No opportunities found")

            time.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
```

---

## Cross-Platform Arbitrage Bot

### Kalshi Integration

```python
# src/platforms/kalshi.py
from kalshi_python import Configuration, KalshiClient
import os

class KalshiAPI:
    def __init__(self):
        config = Configuration()
        config.host = "https://api.elections.kalshi.com/trade-api/v2"

        # Load RSA key
        key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
        if key_path and os.path.exists(key_path):
            with open(key_path) as f:
                config.private_key_pem = f.read()
            config.api_key_id = os.getenv("KALSHI_API_KEY_ID")
            self.client = KalshiClient(config)
            self.authenticated = True
        else:
            self.client = KalshiClient(config)
            self.authenticated = False

    def get_markets(self, limit=200):
        return self.client.get_markets(limit=limit)

    def get_market(self, ticker):
        return self.client.get_market(ticker=ticker)

    def get_orderbook(self, ticker):
        return self.client.get_market_orderbook(ticker=ticker)
```

### Cross-Platform Arbitrage

```python
# src/strategies/cross_platform_arb.py
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class CrossPlatformOpportunity:
    event_name: str
    polymarket_yes: float
    kalshi_no: float
    spread: float
    polymarket_token: str
    kalshi_ticker: str

class CrossPlatformArbitrage:
    def __init__(self, poly_client, kalshi_client, gamma_api):
        self.poly = poly_client
        self.kalshi = kalshi_client
        self.gamma = gamma_api

    def find_matching_markets(self):
        """Find similar markets across platforms"""
        poly_markets = self.gamma.get_markets(active=True, limit=100)
        kalshi_markets = self.kalshi.get_markets(limit=100)

        matches = []

        for pm in poly_markets:
            pm_question = pm.get('question', '').lower()

            for km in kalshi_markets:
                km_title = km.get('title', '').lower()

                # Simple matching (improve with NLP for production)
                if self._similar(pm_question, km_title):
                    matches.append((pm, km))

        return matches

    def _similar(self, text1: str, text2: str) -> bool:
        """Basic similarity check"""
        # Extract key terms
        terms1 = set(re.findall(r'\b\w+\b', text1.lower()))
        terms2 = set(re.findall(r'\b\w+\b', text2.lower()))

        overlap = len(terms1 & terms2)
        total = min(len(terms1), len(terms2))

        return overlap / total > 0.5 if total > 0 else False

    def scan_opportunities(self, min_spread: float = 0.03):
        """Find cross-platform arbitrage opportunities"""
        opportunities = []
        matches = self.find_matching_markets()

        for poly_market, kalshi_market in matches:
            try:
                # Get Polymarket prices
                poly_prices = poly_market.get('outcomePrices', [])
                if len(poly_prices) != 2:
                    continue
                poly_yes = float(poly_prices[0])

                # Get Kalshi prices
                kalshi_book = self.kalshi.get_orderbook(kalshi_market['ticker'])
                kalshi_no = kalshi_book.get('no', {}).get('best_ask', 1.0)

                # Calculate spread
                # Buy YES on Poly + Buy NO on Kalshi
                combined = poly_yes + kalshi_no
                if combined < (1.0 - min_spread):
                    spread = 1.0 - combined

                    opp = CrossPlatformOpportunity(
                        event_name=poly_market['question'][:40],
                        polymarket_yes=poly_yes,
                        kalshi_no=kalshi_no,
                        spread=spread,
                        polymarket_token=poly_market.get('clob_token_ids', [''])[0],
                        kalshi_ticker=kalshi_market['ticker']
                    )
                    opportunities.append(opp)

            except Exception:
                continue

        return sorted(opportunities, key=lambda x: x.spread, reverse=True)
```

---

## Market Making Bot

```python
# src/strategies/market_maker.py
from py_clob_client.order_builder.constants import BUY, SELL
from loguru import logger
import time

class MarketMaker:
    def __init__(self, client, token_id, config=None):
        self.client = client
        self.token_id = token_id
        self.config = config or {
            'spread': 0.04,
            'size': 100,
            'max_position': 1000,
            'update_interval': 30,
            'min_edge': 0.01
        }
        self.active_orders = []

    def get_fair_value(self):
        """Calculate fair value (midpoint by default)"""
        try:
            return float(self.client.get_midpoint(self.token_id))
        except:
            book = self.client.get_order_book(self.token_id)
            bid = float(book['bids'][0]['price']) if book['bids'] else 0.5
            ask = float(book['asks'][0]['price']) if book['asks'] else 0.5
            return (bid + ask) / 2

    def get_position(self):
        """Get current position in this market"""
        positions = self.client.get_positions()
        for p in positions:
            if p.get('asset_id') == self.token_id:
                return float(p.get('size', 0))
        return 0

    def calculate_quotes(self):
        """Calculate bid and ask prices"""
        fair = self.get_fair_value()
        position = self.get_position()
        spread = self.config['spread']

        # Inventory skew
        max_pos = self.config['max_position']
        skew = (position / max_pos) * 0.02 if max_pos > 0 else 0

        bid_price = fair - (spread / 2) - skew
        ask_price = fair + (spread / 2) - skew

        # Clamp to valid range
        bid_price = max(0.01, min(0.99, bid_price))
        ask_price = max(0.01, min(0.99, ask_price))

        return round(bid_price, 2), round(ask_price, 2)

    def cancel_all_orders(self):
        """Cancel existing orders"""
        try:
            self.client.cancel_all()
            self.active_orders = []
        except Exception as e:
            logger.error(f"Cancel failed: {e}")

    def place_quotes(self):
        """Place new bid and ask"""
        bid_price, ask_price = self.calculate_quotes()
        size = self.config['size']

        try:
            # Place bid
            bid_order = self.client.place_order(
                token_id=self.token_id,
                price=bid_price,
                size=size,
                side=BUY
            )
            self.active_orders.append(bid_order)
            logger.info(f"Placed BID: {size} @ {bid_price}")

            # Place ask
            ask_order = self.client.place_order(
                token_id=self.token_id,
                price=ask_price,
                size=size,
                side=SELL
            )
            self.active_orders.append(ask_order)
            logger.info(f"Placed ASK: {size} @ {ask_price}")

        except Exception as e:
            logger.error(f"Order placement failed: {e}")

    def run(self):
        """Main market making loop"""
        logger.info(f"Starting market maker for {self.token_id}")

        while True:
            try:
                self.cancel_all_orders()
                self.place_quotes()

                position = self.get_position()
                logger.info(f"Current position: {position}")

                time.sleep(self.config['update_interval'])

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                self.cancel_all_orders()
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)
```

---

## Whale Following Bot

```python
# src/strategies/whale_follower.py
import requests
from loguru import logger
from dataclasses import dataclass
from typing import List
import time

@dataclass
class WhaleAlert:
    wallet: str
    market: str
    side: str
    size: float
    price: float
    timestamp: float

class WhaleFollower:
    def __init__(self, client, gamma_api, config=None):
        self.client = client
        self.gamma = gamma_api
        self.config = config or {
            'min_trade_size': 10000,  # $10k minimum
            'follow_percentage': 0.1,  # Follow with 10% of whale size
            'max_position': 1000,
            'delay_seconds': 5  # Wait before following
        }
        self.followed_trades = set()

    def get_recent_large_trades(self) -> List[WhaleAlert]:
        """Fetch recent large trades from analytics"""
        # Note: This is a simplified example
        # In production, use WebSocket or analytics API
        alerts = []

        # Example: Query Dune or use Polymarket's trade endpoint
        # This would need actual implementation based on your data source

        return alerts

    def should_follow(self, alert: WhaleAlert) -> bool:
        """Determine if we should follow this trade"""
        # Don't follow same trade twice
        trade_id = f"{alert.wallet}_{alert.market}_{alert.timestamp}"
        if trade_id in self.followed_trades:
            return False

        # Check size threshold
        if alert.size < self.config['min_trade_size']:
            return False

        # Check our position limit
        current_position = self.get_position(alert.market)
        if abs(current_position) >= self.config['max_position']:
            return False

        return True

    def follow_trade(self, alert: WhaleAlert):
        """Execute follow trade"""
        follow_size = alert.size * self.config['follow_percentage']
        follow_size = min(follow_size, self.config['max_position'])

        logger.info(f"Following whale trade: {alert.side} {follow_size} @ {alert.price}")

        # Small delay to avoid front-running detection
        time.sleep(self.config['delay_seconds'])

        try:
            order = self.client.place_order(
                token_id=alert.market,
                price=alert.price,
                size=follow_size,
                side=alert.side
            )
            logger.info(f"Follow order placed: {order}")

            # Track followed trades
            trade_id = f"{alert.wallet}_{alert.market}_{alert.timestamp}"
            self.followed_trades.add(trade_id)

            return order
        except Exception as e:
            logger.error(f"Follow trade failed: {e}")
            return None

    def get_position(self, market):
        positions = self.client.get_positions()
        for p in positions:
            if p.get('asset_id') == market:
                return float(p.get('size', 0))
        return 0
```

---

## Testing & Deployment

### Unit Tests

```python
# tests/test_arbitrage.py
import pytest
from src.strategies.arbitrage import ArbitrageDetector, ArbitrageOpportunity

def test_profit_calculation():
    opp = ArbitrageOpportunity(
        market_id="test",
        question="Test",
        yes_price=0.45,
        no_price=0.50,
        combined=0.95,
        profit_potential=0.05,
        token_ids=("a", "b")
    )
    assert opp.profit_potential == 0.05

def test_no_arb_when_combined_over_one():
    # Combined = 1.02, no arbitrage
    yes_price = 0.55
    no_price = 0.47
    combined = yes_price + no_price
    assert combined > 1.0
```

### Deployment Checklist

```
□ Test on testnet/paper trading first
□ Set DRY_RUN=true initially
□ Implement proper error handling
□ Set up monitoring/alerts
□ Use secure key management
□ Implement rate limiting
□ Add circuit breakers
□ Log all trades
□ Monitor P&L
□ Set position limits
□ Have manual override capability
```

### Running in Production

```bash
# Using screen for persistence
screen -S polybot
python src/main.py

# Or with systemd
# /etc/systemd/system/polybot.service
[Unit]
Description=Polymarket Trading Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/polymarket-bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/youruser/polymarket-bot/venv/bin/python src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Resources

### Official Documentation
- [Polymarket Docs](https://docs.polymarket.com)
- [CLOB Quickstart](https://docs.polymarket.com/developers/CLOB/quickstart)
- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)
- [Kalshi API Docs](https://docs.kalshi.com)

### Community Resources
- [Polymarket Discord](https://discord.gg/polymarket)
- [Kalshi Discord](https://discord.gg/kalshi)
- [GitHub Examples](https://github.com/Polymarket/py-clob-client/tree/main/examples)

### Analytics
- [PolymarketAnalytics](https://polymarketanalytics.com)
- [Dune Analytics](https://dune.com)
- [PolyTrack](https://polytrackhq.app)
