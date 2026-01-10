#!/usr/bin/env python3
"""
Paper Trading Bot for Polymarket Binary Markets

Connects to live orderbook data and simulates market making strategy.
No real money is used - all trades are simulated.

Usage:
    python3 paper_trading/paper_trader.py

The bot will:
1. Load market config from selected_market.json
2. Connect to Polymarket CLOB API for live orderbook data
3. Simulate the market making strategy (post bids on both sides)
4. Track paper positions and P&L
"""
import asyncio
import json
import time
import requests
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import signal
import sys

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    # Profit target
    "target_edge": 0.02,          # Combined bid < $0.98 (2% edge)

    # Bid ladder
    "num_levels": 5,              # Bid levels per side
    "level_spacing": 0.02,        # $0.02 between levels
    "size_per_level": 25,         # Shares per order
    "top_bid_offset": 0.01,       # Distance from mid

    # Risk limits
    "max_inventory_ratio": 1.5,   # Trigger rebalance if ratio > 1.5
    "max_position_size": 2000,    # Max shares per side

    # Timing
    "poll_interval": 2.0,         # Seconds between orderbook polls
    "print_interval": 10.0,       # Seconds between status prints
}

CLOB_API = "https://clob.polymarket.com"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Orderbook:
    bids: List[Dict] = field(default_factory=list)
    asks: List[Dict] = field(default_factory=list)
    timestamp: float = 0

    @property
    def best_bid(self) -> Optional[float]:
        # Bids are sorted ascending - best bid is MAX (highest price buyer)
        if not self.bids:
            return None
        return max(float(b["price"]) for b in self.bids)

    @property
    def best_ask(self) -> Optional[float]:
        # Asks are sorted descending - best ask is MIN (lowest price seller)
        if not self.asks:
            return None
        return min(float(a["price"]) for a in self.asks)

    @property
    def mid(self) -> Optional[float]:
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return None

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None


@dataclass
class PaperOrder:
    id: int
    outcome: str
    side: str
    price: float
    size: float
    status: str = "open"
    created_at: float = field(default_factory=time.time)


@dataclass
class PaperFill:
    timestamp: float
    outcome: str
    side: str
    price: float
    size: float
    order_id: int


@dataclass
class Position:
    outcome_a_shares: float = 0
    outcome_b_shares: float = 0
    usdc_spent: float = 0
    usdc_received: float = 0

    @property
    def complete_sets(self) -> float:
        return min(self.outcome_a_shares, self.outcome_b_shares)

    @property
    def unhedged_a(self) -> float:
        return max(0, self.outcome_a_shares - self.outcome_b_shares)

    @property
    def unhedged_b(self) -> float:
        return max(0, self.outcome_b_shares - self.outcome_a_shares)


# =============================================================================
# PAPER TRADING ENGINE
# =============================================================================

class PaperTradingBot:
    def __init__(self, config: dict, market_config: dict):
        self.config = config
        self.market = market_config

        # Outcome names
        self.outcome_a = market_config["outcome_a"]["name"]
        self.outcome_b = market_config["outcome_b"]["name"]
        self.token_a = market_config["outcome_a"]["token_id"]
        self.token_b = market_config["outcome_b"]["token_id"]

        # Orderbooks
        self.orderbooks = {
            self.outcome_a: Orderbook(),
            self.outcome_b: Orderbook()
        }

        # Paper trading state
        self.position = Position()
        self.open_orders: List[PaperOrder] = []
        self.fills: List[PaperFill] = []
        self.order_counter = 0

        # Stats
        self.start_time = time.time()
        self.last_print_time = 0
        self.poll_count = 0

        # Running flag
        self.running = True

    def fetch_orderbook(self, token_id: str) -> Optional[Orderbook]:
        """Fetch orderbook from CLOB API."""
        try:
            resp = requests.get(
                f"{CLOB_API}/book",
                params={"token_id": token_id},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                return Orderbook(
                    bids=data.get("bids", []),
                    asks=data.get("asks", []),
                    timestamp=time.time()
                )
        except Exception as e:
            print(f"Error fetching orderbook: {e}")
        return None

    def update_orderbooks(self):
        """Update both orderbooks."""
        book_a = self.fetch_orderbook(self.token_a)
        book_b = self.fetch_orderbook(self.token_b)

        if book_a:
            self.orderbooks[self.outcome_a] = book_a
        if book_b:
            self.orderbooks[self.outcome_b] = book_b

        self.poll_count += 1

    def calculate_bid_ladder(self, mid_a: float, mid_b: float) -> tuple:
        """Calculate bid prices ensuring combined < $1.00."""
        cfg = self.config

        # Start with naive top bids
        top_a = mid_a - cfg["top_bid_offset"]
        top_b = mid_b - cfg["top_bid_offset"]

        # Enforce combined < target
        max_combined = 1.0 - cfg["target_edge"]

        if top_a + top_b >= max_combined:
            scale = (max_combined - 0.01) / (top_a + top_b)
            top_a *= scale
            top_b *= scale

        # Ensure positive
        top_a = max(0.01, top_a)
        top_b = max(0.01, top_b)

        # Generate ladders
        bids_a = [round(top_a - i * cfg["level_spacing"], 4)
                  for i in range(cfg["num_levels"])]
        bids_b = [round(top_b - i * cfg["level_spacing"], 4)
                  for i in range(cfg["num_levels"])]

        # Filter out negative prices
        bids_a = [p for p in bids_a if p > 0]
        bids_b = [p for p in bids_b if p > 0]

        return bids_a, bids_b

    def place_paper_order(self, outcome: str, price: float, size: float) -> PaperOrder:
        """Place a simulated buy order."""
        self.order_counter += 1
        order = PaperOrder(
            id=self.order_counter,
            outcome=outcome,
            side="BUY",
            price=price,
            size=size
        )
        self.open_orders.append(order)
        return order

    def cancel_all_orders(self, outcome: str = None):
        """Cancel all or outcome-specific orders."""
        if outcome:
            self.open_orders = [o for o in self.open_orders if o.outcome != outcome]
        else:
            self.open_orders = []

    def check_fills(self):
        """Check if any orders would be filled based on current orderbook."""
        for order in self.open_orders[:]:
            book = self.orderbooks.get(order.outcome)
            if not book or not book.asks:
                continue

            # A buy order fills if best ask <= our bid price
            # (simulating someone selling into our bid)
            best_ask = book.best_ask

            if best_ask is not None and best_ask <= order.price:
                self.execute_fill(order, best_ask)

    def execute_fill(self, order: PaperOrder, fill_price: float):
        """Execute a paper fill."""
        order.status = "filled"
        self.open_orders.remove(order)

        fill = PaperFill(
            timestamp=time.time(),
            outcome=order.outcome,
            side=order.side,
            price=fill_price,
            size=order.size,
            order_id=order.id
        )
        self.fills.append(fill)

        # Update position
        cost = fill_price * order.size
        self.position.usdc_spent += cost

        if order.outcome == self.outcome_a:
            self.position.outcome_a_shares += order.size
        else:
            self.position.outcome_b_shares += order.size

        print(f"\n[FILL] Bought {order.size:.0f} {order.outcome} @ ${fill_price:.4f} (cost: ${cost:.2f})")

    def update_orders(self):
        """Update paper orders based on current market state."""
        book_a = self.orderbooks.get(self.outcome_a)
        book_b = self.orderbooks.get(self.outcome_b)

        if not book_a or not book_b:
            return

        mid_a = book_a.mid
        mid_b = book_b.mid

        if mid_a is None or mid_b is None:
            return

        # Check if spreads are tradeable
        if book_a.spread and book_a.spread > 0.5:
            return  # Spread too wide, wait
        if book_b.spread and book_b.spread > 0.5:
            return

        # Calculate new bid ladder
        bids_a, bids_b = self.calculate_bid_ladder(mid_a, mid_b)

        # Cancel existing orders
        self.cancel_all_orders()

        # Place new orders
        cfg = self.config

        for price in bids_a:
            if self.position.outcome_a_shares < cfg["max_position_size"]:
                self.place_paper_order(self.outcome_a, price, cfg["size_per_level"])

        for price in bids_b:
            if self.position.outcome_b_shares < cfg["max_position_size"]:
                self.place_paper_order(self.outcome_b, price, cfg["size_per_level"])

    def print_status(self):
        """Print current status."""
        now = time.time()
        runtime = now - self.start_time

        book_a = self.orderbooks.get(self.outcome_a)
        book_b = self.orderbooks.get(self.outcome_b)
        pos = self.position

        print("\n" + "="*70)
        print(f"PAPER TRADING STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"Runtime: {runtime/60:.1f} min | Polls: {self.poll_count} | Fills: {len(self.fills)}")
        print("="*70)

        print(f"\nMARKET: {self.market['question']}")

        print(f"\nORDERBOOK:")
        if book_a and book_a.best_bid is not None:
            print(f"  {self.outcome_a}: bid=${book_a.best_bid:.4f} ask=${book_a.best_ask:.4f} spread=${book_a.spread:.4f}")
        if book_b and book_b.best_bid is not None:
            print(f"  {self.outcome_b}: bid=${book_b.best_bid:.4f} ask=${book_b.best_ask:.4f} spread=${book_b.spread:.4f}")

        if book_a and book_b and book_a.mid and book_b.mid:
            print(f"  Price Sum: ${book_a.mid + book_b.mid:.4f}")

        print(f"\nPOSITION:")
        print(f"  {self.outcome_a}: {pos.outcome_a_shares:.0f} shares")
        print(f"  {self.outcome_b}: {pos.outcome_b_shares:.0f} shares")
        print(f"  Complete Sets: {pos.complete_sets:.0f}")
        print(f"  Unhedged {self.outcome_a}: {pos.unhedged_a:.0f}")
        print(f"  Unhedged {self.outcome_b}: {pos.unhedged_b:.0f}")
        print(f"  USDC Spent: ${pos.usdc_spent:.2f}")

        print(f"\nOPEN ORDERS: {len(self.open_orders)}")
        for o in self.open_orders[:3]:
            print(f"  BUY {o.size:.0f} {o.outcome} @ ${o.price:.4f}")
        if len(self.open_orders) > 3:
            print(f"  ... and {len(self.open_orders) - 3} more")

        # P&L estimate
        if pos.complete_sets > 0:
            avg_cost_per_set = pos.usdc_spent / pos.complete_sets if pos.complete_sets > 0 else 0
            guaranteed_pnl = pos.complete_sets * (1.0 - avg_cost_per_set / 2)
            print(f"\nP&L ESTIMATE:")
            print(f"  Avg cost per share: ${pos.usdc_spent / (pos.outcome_a_shares + pos.outcome_b_shares):.4f}" if (pos.outcome_a_shares + pos.outcome_b_shares) > 0 else "")
            print(f"  Guaranteed P&L (from sets): ${guaranteed_pnl:.2f}")

        print("="*70)

    async def run(self):
        """Main trading loop."""
        print("\n" + "="*70)
        print("PAPER TRADING BOT STARTED")
        print("="*70)
        print(f"\nMarket: {self.market['question']}")
        print(f"End Time: {self.market.get('end_date', 'Unknown')}")
        print(f"Polling interval: {self.config['poll_interval']}s")
        print("\nPress Ctrl+C to stop\n")

        while self.running:
            try:
                # Update orderbooks
                self.update_orderbooks()

                # Check for fills
                self.check_fills()

                # Update orders
                self.update_orders()

                # Print status periodically
                now = time.time()
                if now - self.last_print_time >= self.config["print_interval"]:
                    self.print_status()
                    self.last_print_time = now

                # Wait
                await asyncio.sleep(self.config["poll_interval"])

            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(1)

        # Final status
        print("\n" + "="*70)
        print("PAPER TRADING STOPPED")
        print("="*70)
        self.print_status()

        # Save results
        self.save_results()

    def save_results(self):
        """Save trading results to file."""
        results = {
            "market": self.market,
            "config": self.config,
            "runtime_seconds": time.time() - self.start_time,
            "poll_count": self.poll_count,
            "position": {
                "outcome_a_shares": self.position.outcome_a_shares,
                "outcome_b_shares": self.position.outcome_b_shares,
                "complete_sets": self.position.complete_sets,
                "usdc_spent": self.position.usdc_spent
            },
            "fills": [
                {
                    "timestamp": f.timestamp,
                    "outcome": f.outcome,
                    "price": f.price,
                    "size": f.size
                }
                for f in self.fills
            ],
            "saved_at": datetime.now(timezone.utc).isoformat()
        }

        filepath = "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/results.json"
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {filepath}")

    def stop(self):
        """Stop the bot."""
        self.running = False


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Load market config
    config_path = "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/selected_market.json"

    try:
        with open(config_path) as f:
            market_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Market config not found at {config_path}")
        print("Run market_scanner.py first to select a market")
        sys.exit(1)

    # Create bot
    bot = PaperTradingBot(CONFIG, market_config)

    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nStopping...")
        bot.stop()

    signal.signal(signal.SIGINT, signal_handler)

    # Run
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
