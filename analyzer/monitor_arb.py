"""
Real-time arbitrage opportunity monitor for Polymarket 15-minute markets.
Tracks when UP + DOWN prices go below $1.00.
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# APIs
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


def get_active_15min_markets() -> List[Dict]:
    """Find currently active 15-minute BTC/ETH markets"""

    print("Fetching active 15-minute markets...")

    # Search for active Up/Down markets
    resp = requests.get(
        f"{GAMMA_API}/markets",
        params={
            "active": "true",
            "closed": "false",
            "limit": 100
        },
        timeout=30
    )
    resp.raise_for_status()
    markets = resp.json()

    # Filter for 15-minute crypto markets
    fifteen_min_markets = []
    for m in markets:
        question = m.get("question", "")
        if "Up or Down" in question and ("Bitcoin" in question or "Ethereum" in question):
            fifteen_min_markets.append(m)

    return fifteen_min_markets


def get_market_tokens(market: Dict) -> Tuple[Optional[str], Optional[str]]:
    """Get token IDs for Up and Down outcomes"""

    tokens = market.get("tokens", [])
    up_token = None
    down_token = None

    for t in tokens:
        outcome = t.get("outcome", "").lower()
        if outcome == "up":
            up_token = t.get("token_id")
        elif outcome == "down":
            down_token = t.get("token_id")

    return up_token, down_token


def get_orderbook_prices(token_id: str) -> Tuple[Optional[float], Optional[float]]:
    """Get best bid and ask for a token"""

    try:
        resp = requests.get(
            f"{CLOB_API}/book",
            params={"token_id": token_id},
            timeout=10
        )
        resp.raise_for_status()
        book = resp.json()

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        best_bid = float(bids[0]["price"]) if bids else None
        best_ask = float(asks[0]["price"]) if asks else None

        return best_bid, best_ask

    except Exception as e:
        return None, None


def get_midpoint_price(token_id: str) -> Optional[float]:
    """Get midpoint price for a token"""

    try:
        resp = requests.get(
            f"{CLOB_API}/midpoint",
            params={"token_id": token_id},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data.get("mid", 0))
    except:
        return None


def monitor_market(market: Dict, duration_seconds: int = 300, interval: float = 1.0):
    """
    Monitor a single market for arbitrage opportunities.

    Args:
        market: Market dict from Gamma API
        duration_seconds: How long to monitor (default 5 minutes)
        interval: Seconds between checks (default 1 second)
    """

    question = market.get("question", "Unknown")
    up_token, down_token = get_market_tokens(market)

    if not up_token or not down_token:
        print(f"Could not find tokens for: {question}")
        return

    print(f"\n{'='*70}")
    print(f"MONITORING: {question}")
    print(f"UP token:   {up_token[:20]}...")
    print(f"DOWN token: {down_token[:20]}...")
    print(f"Duration:   {duration_seconds} seconds")
    print(f"{'='*70}\n")

    # Stats tracking
    checks = 0
    opportunities = 0
    opportunity_log = []
    prices_log = []

    start_time = time.time()

    print(f"{'Time':<12} {'UP Ask':>8} {'DOWN Ask':>9} {'Combined':>10} {'Spread':>8} {'Status'}")
    print("-" * 60)

    while time.time() - start_time < duration_seconds:
        checks += 1

        # Get orderbook prices (best asks = what we'd pay to buy)
        up_bid, up_ask = get_orderbook_prices(up_token)
        down_bid, down_ask = get_orderbook_prices(down_token)

        timestamp = datetime.now().strftime("%H:%M:%S")

        if up_ask and down_ask:
            combined = up_ask + down_ask
            spread = 1.0 - combined

            # Log all prices
            prices_log.append({
                "timestamp": timestamp,
                "up_ask": up_ask,
                "down_ask": down_ask,
                "combined": combined,
                "spread": spread
            })

            # Check for arbitrage
            if combined < 1.0:
                opportunities += 1
                status = f"*** ARB ${spread:.4f} ***"
                opportunity_log.append({
                    "timestamp": timestamp,
                    "up_ask": up_ask,
                    "down_ask": down_ask,
                    "combined": combined,
                    "profit_per_pair": spread
                })
            elif combined < 1.01:
                status = "Near arb"
            else:
                status = ""

            print(f"{timestamp:<12} ${up_ask:>7.4f} ${down_ask:>8.4f} ${combined:>9.4f} {spread:>+8.4f} {status}")
        else:
            print(f"{timestamp:<12} {'N/A':>8} {'N/A':>9} {'N/A':>10} {'N/A':>8} No data")

        time.sleep(interval)

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total checks:        {checks}")
    print(f"Arb opportunities:   {opportunities}")
    print(f"Arb frequency:       {opportunities/checks*100:.1f}%")

    if prices_log:
        spreads = [p["spread"] for p in prices_log]
        print(f"\nSpread stats:")
        print(f"  Min spread:  {min(spreads):+.4f} (best: ${-min(spreads):.4f} under $1)")
        print(f"  Max spread:  {max(spreads):+.4f}")
        print(f"  Avg spread:  {sum(spreads)/len(spreads):+.4f}")

    if opportunity_log:
        print(f"\nArbitrage opportunities detected:")
        for opp in opportunity_log[:10]:  # Show first 10
            print(f"  {opp['timestamp']}: UP ${opp['up_ask']:.4f} + DOWN ${opp['down_ask']:.4f} = ${opp['combined']:.4f} (profit: ${opp['profit_per_pair']:.4f})")

        if len(opportunity_log) > 10:
            print(f"  ... and {len(opportunity_log) - 10} more")

    return {
        "checks": checks,
        "opportunities": opportunities,
        "frequency": opportunities / checks if checks > 0 else 0,
        "prices_log": prices_log,
        "opportunity_log": opportunity_log
    }


def main():
    """Main monitoring loop"""

    print("=" * 70)
    print("POLYMARKET 15-MINUTE ARBITRAGE MONITOR")
    print("=" * 70)

    # Get active markets
    markets = get_active_15min_markets()

    if not markets:
        print("No active 15-minute markets found!")
        print("\nNote: Markets are only active during certain hours.")
        print("Trying to find any recent market for testing...")

        # Try to get any Up/Down market
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"limit": 200},
            timeout=30
        )
        all_markets = resp.json()

        for m in all_markets:
            question = m.get("question", "")
            if "Up or Down" in question and ("Bitcoin" in question or "Ethereum" in question):
                markets.append(m)
                if len(markets) >= 3:
                    break

    print(f"\nFound {len(markets)} markets:")
    for i, m in enumerate(markets[:10]):
        print(f"  {i+1}. {m.get('question', 'Unknown')[:60]}")

    if not markets:
        print("No markets available to monitor.")
        return

    # Monitor the first active market
    print("\n" + "=" * 70)
    print("Starting monitor on first market...")
    print("Press Ctrl+C to stop")
    print("=" * 70)

    try:
        # Monitor for 5 minutes with 1-second intervals
        result = monitor_market(markets[0], duration_seconds=300, interval=1.0)

        # Save results
        with open("data/arb_monitor_results.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nResults saved to data/arb_monitor_results.json")

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")


if __name__ == "__main__":
    main()
