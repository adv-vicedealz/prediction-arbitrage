#!/usr/bin/env python3
"""
Continuous Paper Trading System

Automatically:
1. Discovers new BTC Up/Down 15-minute markets
2. Paper trades each market
3. Records results after resolution
4. Analyzes performance over time

Run with: python3 paper_trading/continuous_trader.py
"""
import requests
import json
import time
import random
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
import signal
import sys

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    # Trading parameters
    "target_edge": 0.03,          # Target 3% edge (combined < $0.97)
    "size_per_fill": 25,          # Shares per simulated fill
    "fill_probability": 0.40,     # 40% chance of fill per poll if competitive

    # Inventory management
    "max_inventory_ratio": 1.5,   # Rebalance if ratio > 1.5
    "rebalance_size": 25,         # Shares to rebalance

    # Timing
    "poll_interval": 3,           # Seconds between polls
    "market_check_interval": 60,  # Seconds between checking for new markets

    # Data storage
    "data_dir": "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/data",
    "results_file": "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/all_results.json",
}

CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Fill:
    timestamp: float
    outcome: str
    price: float
    size: float
    fill_type: str  # "maker" or "rebalance"


@dataclass
class MarketSession:
    market_id: str
    question: str
    slug: str
    start_time: float
    end_time: Optional[float] = None

    # Tokens
    up_token: str = ""
    down_token: str = ""

    # Position tracking
    up_shares: float = 0
    down_shares: float = 0
    up_cost: float = 0
    down_cost: float = 0

    # Fills
    fills: List[Dict] = field(default_factory=list)

    # Price history
    price_history: List[Dict] = field(default_factory=list)

    # Resolution
    winner: Optional[str] = None
    resolved: bool = False

    # Metrics
    total_polls: int = 0
    total_fills: int = 0
    rebalance_count: int = 0
    max_imbalance_ratio: float = 1.0

    @property
    def complete_sets(self) -> float:
        return min(self.up_shares, self.down_shares)

    @property
    def unhedged_up(self) -> float:
        return max(0, self.up_shares - self.down_shares)

    @property
    def unhedged_down(self) -> float:
        return max(0, self.down_shares - self.up_shares)

    @property
    def avg_up_price(self) -> float:
        return self.up_cost / self.up_shares if self.up_shares > 0 else 0

    @property
    def avg_down_price(self) -> float:
        return self.down_cost / self.down_shares if self.down_shares > 0 else 0

    @property
    def combined_avg(self) -> float:
        return self.avg_up_price + self.avg_down_price

    @property
    def edge(self) -> float:
        return 1.0 - self.combined_avg if self.combined_avg > 0 else 0

    @property
    def guaranteed_pnl(self) -> float:
        return self.complete_sets * self.edge

    def calculate_actual_pnl(self) -> float:
        if not self.resolved or not self.winner:
            return 0

        pnl = self.guaranteed_pnl

        if self.winner == "Up":
            pnl += self.unhedged_up * 1.0  # Unhedged Up pays $1
            pnl -= self.unhedged_down * self.avg_down_price  # Lost cost of unhedged Down
        else:
            pnl += self.unhedged_down * 1.0  # Unhedged Down pays $1
            pnl -= self.unhedged_up * self.avg_up_price  # Lost cost of unhedged Up

        return pnl


# =============================================================================
# MARKET DISCOVERY
# =============================================================================

def find_btc_updown_markets() -> List[Dict]:
    """Find active BTC Up/Down 15-minute markets."""
    try:
        resp = requests.get(f"{GAMMA_API}/markets", params={
            "active": "true",
            "closed": "false",
            "limit": 50
        }, timeout=30)

        markets = resp.json()

        btc_markets = []
        for m in markets:
            slug = m.get("slug", "").lower()
            if "btc-updown-15m" in slug:
                btc_markets.append(m)

        return btc_markets
    except Exception as e:
        print(f"Error finding markets: {e}")
        return []


def get_market_details(condition_id: str) -> Optional[Dict]:
    """Get full market details from CLOB API."""
    try:
        resp = requests.get(f"{CLOB_API}/markets/{condition_id}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def get_orderbook(token_id: str) -> Optional[Dict]:
    """Get orderbook for a token."""
    try:
        resp = requests.get(f"{CLOB_API}/book", params={"token_id": token_id}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            bids = data.get("bids", [])
            asks = data.get("asks", [])

            best_bid = max(float(b["price"]) for b in bids) if bids else None
            best_ask = min(float(a["price"]) for a in asks) if asks else None

            return {
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": best_ask - best_bid if best_bid and best_ask else None
            }
    except:
        pass
    return None


# =============================================================================
# PAPER TRADING ENGINE
# =============================================================================

class ContinuousTrader:
    def __init__(self, config: dict):
        self.config = config
        self.running = True
        self.current_session: Optional[MarketSession] = None
        self.completed_sessions: List[MarketSession] = []
        self.known_markets: set = set()

        # Create data directory
        os.makedirs(config["data_dir"], exist_ok=True)

        # Load previous results
        self.load_results()

    def load_results(self):
        """Load previous session results."""
        try:
            if os.path.exists(self.config["results_file"]):
                with open(self.config["results_file"]) as f:
                    data = json.load(f)
                    self.known_markets = set(data.get("known_markets", []))
                    print(f"Loaded {len(self.known_markets)} known markets")
        except Exception as e:
            print(f"Error loading results: {e}")

    def save_results(self):
        """Save all session results."""
        try:
            results = {
                "known_markets": list(self.known_markets),
                "sessions": [self.session_to_dict(s) for s in self.completed_sessions],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            with open(self.config["results_file"], "w") as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            print(f"Error saving results: {e}")

    def session_to_dict(self, session: MarketSession) -> dict:
        """Convert session to dictionary for JSON."""
        return {
            "market_id": session.market_id,
            "question": session.question,
            "slug": session.slug,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "up_shares": session.up_shares,
            "down_shares": session.down_shares,
            "up_cost": session.up_cost,
            "down_cost": session.down_cost,
            "complete_sets": session.complete_sets,
            "unhedged_up": session.unhedged_up,
            "unhedged_down": session.unhedged_down,
            "avg_up_price": session.avg_up_price,
            "avg_down_price": session.avg_down_price,
            "combined_avg": session.combined_avg,
            "edge": session.edge,
            "guaranteed_pnl": session.guaranteed_pnl,
            "winner": session.winner,
            "resolved": session.resolved,
            "actual_pnl": session.calculate_actual_pnl() if session.resolved else None,
            "total_polls": session.total_polls,
            "total_fills": session.total_fills,
            "rebalance_count": session.rebalance_count,
            "max_imbalance_ratio": session.max_imbalance_ratio,
            "fills": session.fills,
            "price_history": session.price_history[-100:]  # Last 100 price points
        }

    def find_new_market(self) -> Optional[Dict]:
        """Find a new market to trade."""
        markets = find_btc_updown_markets()

        for m in markets:
            market_id = m.get("conditionId")
            if market_id and market_id not in self.known_markets:
                # Get full details
                details = get_market_details(market_id)
                if details and details.get("accepting_orders"):
                    tokens = details.get("tokens", [])
                    if len(tokens) == 2:
                        return {
                            "market_id": market_id,
                            "question": m.get("question"),
                            "slug": m.get("slug"),
                            "end_date": m.get("endDate"),
                            "tokens": tokens
                        }

        return None

    def start_session(self, market: Dict):
        """Start a new trading session."""
        tokens = market["tokens"]
        up_token = None
        down_token = None

        for t in tokens:
            if t.get("outcome") == "Up":
                up_token = t.get("token_id")
            elif t.get("outcome") == "Down":
                down_token = t.get("token_id")

        self.current_session = MarketSession(
            market_id=market["market_id"],
            question=market["question"],
            slug=market["slug"],
            start_time=time.time(),
            up_token=up_token,
            down_token=down_token
        )

        self.known_markets.add(market["market_id"])

        print("\n" + "="*70)
        print(f"NEW SESSION: {market['question']}")
        print(f"End: {market.get('end_date')}")
        print("="*70 + "\n")

    def trade_session(self):
        """Execute one trading iteration."""
        if not self.current_session:
            return

        session = self.current_session

        # Get orderbooks
        up_book = get_orderbook(session.up_token)
        down_book = get_orderbook(session.down_token)

        if not up_book or not down_book:
            return

        if up_book["best_bid"] is None or down_book["best_bid"] is None:
            return

        session.total_polls += 1

        # Current prices
        up_mid = (up_book["best_bid"] + up_book["best_ask"]) / 2
        down_mid = (down_book["best_bid"] + down_book["best_ask"]) / 2
        up_spread = up_book["spread"] or 1
        down_spread = down_book["spread"] or 1

        # Record price
        session.price_history.append({
            "t": time.time(),
            "up": up_mid,
            "down": down_mid
        })

        # Calculate our bids
        target = 1.0 - self.config["target_edge"]
        our_up_bid = up_mid - 0.01
        our_down_bid = down_mid - 0.01

        if our_up_bid + our_down_bid >= target:
            scale = (target - 0.01) / (our_up_bid + our_down_bid)
            our_up_bid *= scale
            our_down_bid *= scale

        # Track inventory ratio
        if session.down_shares > 0:
            ratio = session.up_shares / session.down_shares
        else:
            ratio = 999 if session.up_shares > 0 else 1.0

        session.max_imbalance_ratio = max(session.max_imbalance_ratio, max(ratio, 1/ratio if ratio > 0 else 1))

        # Simulate fills (random based on spread tightness)
        fill_up = random.random() < self.config["fill_probability"] and up_spread <= 0.05
        fill_down = random.random() < self.config["fill_probability"] and down_spread <= 0.05

        # Inventory-based adjustment: less likely to fill the heavy side
        if ratio > self.config["max_inventory_ratio"]:
            fill_up = fill_up and random.random() < 0.3  # Reduce Up fills
        elif ratio < 1 / self.config["max_inventory_ratio"]:
            fill_down = fill_down and random.random() < 0.3  # Reduce Down fills

        # Execute fills
        if fill_up:
            session.up_shares += self.config["size_per_fill"]
            session.up_cost += our_up_bid * self.config["size_per_fill"]
            session.fills.append({
                "t": time.time(),
                "outcome": "Up",
                "price": our_up_bid,
                "size": self.config["size_per_fill"],
                "type": "maker"
            })
            session.total_fills += 1

        if fill_down:
            session.down_shares += self.config["size_per_fill"]
            session.down_cost += our_down_bid * self.config["size_per_fill"]
            session.fills.append({
                "t": time.time(),
                "outcome": "Down",
                "price": our_down_bid,
                "size": self.config["size_per_fill"],
                "type": "maker"
            })
            session.total_fills += 1

        # Rebalancing logic
        if session.up_shares > 0 and session.down_shares > 0:
            ratio = session.up_shares / session.down_shares

            if ratio > self.config["max_inventory_ratio"]:
                # Sell some Up (simulated)
                sell_size = min(self.config["rebalance_size"], session.unhedged_up)
                if sell_size > 0:
                    # Sell at bid price (worse price)
                    sell_price = up_book["best_bid"]
                    session.up_shares -= sell_size
                    session.up_cost -= sell_size * session.avg_up_price
                    # We receive USDC back
                    session.fills.append({
                        "t": time.time(),
                        "outcome": "Up",
                        "price": sell_price,
                        "size": -sell_size,
                        "type": "rebalance"
                    })
                    session.rebalance_count += 1

            elif ratio < 1 / self.config["max_inventory_ratio"]:
                # Sell some Down
                sell_size = min(self.config["rebalance_size"], session.unhedged_down)
                if sell_size > 0:
                    sell_price = down_book["best_bid"]
                    session.down_shares -= sell_size
                    session.down_cost -= sell_size * session.avg_down_price
                    session.fills.append({
                        "t": time.time(),
                        "outcome": "Down",
                        "price": sell_price,
                        "size": -sell_size,
                        "type": "rebalance"
                    })
                    session.rebalance_count += 1

        # Print status every 10 polls
        if session.total_polls % 10 == 1:
            elapsed = time.time() - session.start_time
            print(f"[{elapsed/60:.1f}m] Up=${up_mid:.2f} Dn=${down_mid:.2f} | "
                  f"Pos:{session.up_shares:.0f}/{session.down_shares:.0f} | "
                  f"Sets:{session.complete_sets:.0f} | "
                  f"Edge:{session.edge*100:.1f}%")

    def check_market_ended(self) -> bool:
        """Check if current market has ended."""
        if not self.current_session:
            return False

        details = get_market_details(self.current_session.market_id)
        if details:
            if details.get("closed"):
                return True

            # Check if tokens have winner
            tokens = details.get("tokens", [])
            for t in tokens:
                if t.get("winner"):
                    self.current_session.winner = t.get("outcome")
                    self.current_session.resolved = True
                    return True

        return False

    def end_session(self):
        """End the current session and record results."""
        if not self.current_session:
            return

        session = self.current_session
        session.end_time = time.time()

        # Try to get resolution
        details = get_market_details(session.market_id)
        if details:
            tokens = details.get("tokens", [])
            for t in tokens:
                if t.get("winner"):
                    session.winner = t.get("outcome")
                    session.resolved = True

        # Print summary
        print("\n" + "="*70)
        print("SESSION ENDED")
        print("="*70)
        print(f"Market: {session.question}")
        print(f"Duration: {(session.end_time - session.start_time)/60:.1f} minutes")
        print(f"Fills: {session.total_fills}")
        print(f"Rebalances: {session.rebalance_count}")
        print(f"\nPosition: {session.up_shares:.0f} Up, {session.down_shares:.0f} Down")
        print(f"Complete Sets: {session.complete_sets:.0f}")
        print(f"Edge: {session.edge*100:.2f}%")
        print(f"Guaranteed P&L: ${session.guaranteed_pnl:.2f}")

        if session.resolved:
            print(f"\nWinner: {session.winner}")
            print(f"Actual P&L: ${session.calculate_actual_pnl():.2f}")
        else:
            print("\nAwaiting resolution...")

        # Save session
        self.completed_sessions.append(session)
        self.save_results()

        # Save individual session file
        session_file = os.path.join(
            self.config["data_dir"],
            f"session_{session.slug}_{int(session.start_time)}.json"
        )
        with open(session_file, "w") as f:
            json.dump(self.session_to_dict(session), f, indent=2)

        print(f"\nSaved to: {session_file}")

        self.current_session = None

    def print_overall_stats(self):
        """Print overall performance statistics."""
        if not self.completed_sessions:
            print("\nNo completed sessions yet.")
            return

        resolved = [s for s in self.completed_sessions if s.resolved]

        print("\n" + "="*70)
        print("OVERALL PERFORMANCE")
        print("="*70)

        print(f"\nTotal Sessions: {len(self.completed_sessions)}")
        print(f"Resolved: {len(resolved)}")

        if resolved:
            total_pnl = sum(s.calculate_actual_pnl() for s in resolved)
            total_sets = sum(s.complete_sets for s in resolved)
            avg_edge = sum(s.edge for s in resolved) / len(resolved)
            avg_imbalance = sum(s.max_imbalance_ratio for s in resolved) / len(resolved)

            print(f"\nTotal P&L: ${total_pnl:.2f}")
            print(f"Total Complete Sets: {total_sets:.0f}")
            print(f"Average Edge: {avg_edge*100:.2f}%")
            print(f"Average Max Imbalance: {avg_imbalance:.2f}")

            # Win/loss breakdown
            wins = [s for s in resolved if s.calculate_actual_pnl() > 0]
            losses = [s for s in resolved if s.calculate_actual_pnl() <= 0]
            print(f"\nWins: {len(wins)} | Losses: {len(losses)}")

    def run(self):
        """Main loop."""
        print("="*70)
        print("CONTINUOUS PAPER TRADING SYSTEM")
        print("="*70)
        print(f"Target Edge: {self.config['target_edge']*100:.0f}%")
        print(f"Fill Probability: {self.config['fill_probability']*100:.0f}%")
        print(f"Max Inventory Ratio: {self.config['max_inventory_ratio']}")
        print("\nPress Ctrl+C to stop\n")

        last_market_check = 0

        while self.running:
            try:
                now = time.time()

                # Check for new markets periodically
                if not self.current_session and now - last_market_check > self.config["market_check_interval"]:
                    last_market_check = now
                    print("Scanning for new markets...")

                    market = self.find_new_market()
                    if market:
                        self.start_session(market)
                    else:
                        print("No new markets found. Waiting...")

                # Trade current session
                if self.current_session:
                    self.trade_session()

                    # Check if market ended
                    if self.check_market_ended():
                        self.end_session()

                time.sleep(self.config["poll_interval"])

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

        # Cleanup
        if self.current_session:
            self.end_session()

        self.print_overall_stats()
        self.save_results()
        print("\nShutdown complete.")

    def stop(self):
        self.running = False


# =============================================================================
# MAIN
# =============================================================================

def main():
    trader = ContinuousTrader(CONFIG)

    def signal_handler(sig, frame):
        print("\nStopping...")
        trader.stop()

    signal.signal(signal.SIGINT, signal_handler)

    trader.run()


if __name__ == "__main__":
    main()
