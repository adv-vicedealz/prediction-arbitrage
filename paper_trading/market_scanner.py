#!/usr/bin/env python3
"""
Market Scanner - Find active binary markets suitable for market making.

Criteria for good markets:
1. Binary (exactly 2 outcomes)
2. Active and not closed
3. Has liquidity (orderbook depth)
4. Reasonable volume
5. Ends soon (for faster testing) or has ongoing activity
"""
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
import time

CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


def fetch_all_clob_markets(max_pages: int = 10) -> list:
    """Fetch all markets from CLOB API with pagination."""
    all_markets = []
    next_cursor = ""

    for i in range(max_pages):
        try:
            resp = requests.get(
                f"{CLOB_API}/markets",
                params={"next_cursor": next_cursor} if next_cursor else {},
                timeout=30
            )
            data = resp.json()

            if isinstance(data, dict):
                markets = data.get("data", data.get("markets", []))
                next_cursor = data.get("next_cursor", "")
            else:
                markets = data
                next_cursor = ""

            all_markets.extend(markets)
            print(f"  Fetched page {i+1}: {len(markets)} markets (total: {len(all_markets)})")

            if not next_cursor or len(markets) == 0:
                break

        except Exception as e:
            print(f"  Error on page {i+1}: {e}")
            break

    return all_markets


def get_orderbook(token_id: str) -> Optional[dict]:
    """Fetch current orderbook for a token."""
    try:
        resp = requests.get(
            f"{CLOB_API}/book",
            params={"token_id": token_id},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def analyze_market(market: dict) -> dict:
    """Analyze a market for suitability."""
    tokens = market.get("tokens", [])

    # Must be binary
    if len(tokens) != 2:
        return {"suitable": False, "reason": "Not binary"}

    # Check activity
    active = market.get("active", False)
    closed = market.get("closed", True)

    if not active or closed:
        return {"suitable": False, "reason": "Not active or closed"}

    # Get token info
    token_a = tokens[0]
    token_b = tokens[1]

    # Check orderbooks
    book_a = get_orderbook(token_a.get("token_id", ""))
    book_b = get_orderbook(token_b.get("token_id", ""))

    if not book_a or not book_b:
        return {"suitable": False, "reason": "No orderbook data"}

    # Analyze liquidity
    bids_a = book_a.get("bids", [])
    asks_a = book_a.get("asks", [])
    bids_b = book_b.get("bids", [])
    asks_b = book_b.get("asks", [])

    # Need bids and asks on both sides
    if not bids_a or not asks_a or not bids_b or not asks_b:
        return {"suitable": False, "reason": "Missing orderbook depth"}

    # Calculate metrics
    best_bid_a = float(bids_a[0]["price"]) if bids_a else 0
    best_ask_a = float(asks_a[0]["price"]) if asks_a else 1
    best_bid_b = float(bids_b[0]["price"]) if bids_b else 0
    best_ask_b = float(asks_b[0]["price"]) if asks_b else 1

    spread_a = best_ask_a - best_bid_a
    spread_b = best_ask_b - best_bid_b
    mid_a = (best_bid_a + best_ask_a) / 2
    mid_b = (best_bid_b + best_ask_b) / 2

    # Calculate total depth
    depth_a = sum(float(b["size"]) for b in bids_a[:5]) + sum(float(a["size"]) for a in asks_a[:5])
    depth_b = sum(float(b["size"]) for b in bids_b[:5]) + sum(float(a["size"]) for a in asks_b[:5])

    # Check if prices make sense (should sum to ~1)
    price_sum = mid_a + mid_b

    return {
        "suitable": True,
        "token_a": {
            "outcome": token_a.get("outcome"),
            "token_id": token_a.get("token_id"),
            "best_bid": best_bid_a,
            "best_ask": best_ask_a,
            "mid": mid_a,
            "spread": spread_a,
            "depth": depth_a
        },
        "token_b": {
            "outcome": token_b.get("outcome"),
            "token_id": token_b.get("token_id"),
            "best_bid": best_bid_b,
            "best_ask": best_ask_b,
            "mid": mid_b,
            "spread": spread_b,
            "depth": depth_b
        },
        "price_sum": price_sum,
        "total_depth": depth_a + depth_b,
        "avg_spread": (spread_a + spread_b) / 2
    }


def score_market(market: dict, analysis: dict) -> float:
    """Score a market for market-making suitability."""
    if not analysis.get("suitable"):
        return 0

    score = 0

    # Liquidity score (depth)
    depth = analysis.get("total_depth", 0)
    score += min(depth / 1000, 10)  # Max 10 points

    # Spread score (tighter is better)
    spread = analysis.get("avg_spread", 1)
    if spread < 0.02:
        score += 10
    elif spread < 0.05:
        score += 7
    elif spread < 0.10:
        score += 4
    else:
        score += 1

    # Price sum score (closer to 1.0 is better)
    price_sum = analysis.get("price_sum", 0)
    if 0.95 <= price_sum <= 1.05:
        score += 10
    elif 0.90 <= price_sum <= 1.10:
        score += 5

    # End date score (sooner is better for testing)
    end_date = market.get("end_date_iso")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_to_end = (end_dt - now).days

            if 0 < days_to_end <= 1:
                score += 15  # Ends very soon - great for testing
            elif 1 < days_to_end <= 7:
                score += 10
            elif 7 < days_to_end <= 30:
                score += 5
        except:
            pass

    return score


def scan_for_markets(max_results: int = 10) -> list:
    """Scan for suitable binary markets."""
    print("Scanning for suitable binary markets...")
    print("=" * 60)

    # Fetch all markets
    print("\n1. Fetching markets from CLOB API...")
    all_markets = fetch_all_clob_markets(max_pages=5)
    print(f"   Total markets: {len(all_markets)}")

    # Filter binary markets
    print("\n2. Filtering binary markets...")
    binary_markets = [m for m in all_markets if len(m.get("tokens", [])) == 2]
    print(f"   Binary markets: {len(binary_markets)}")

    # Filter active markets
    active_markets = [m for m in binary_markets if m.get("active") and not m.get("closed")]
    print(f"   Active binary markets: {len(active_markets)}")

    # Analyze and score markets
    print("\n3. Analyzing market quality (this may take a while)...")
    scored_markets = []

    for i, market in enumerate(active_markets[:100]):  # Limit to first 100 for speed
        if i % 10 == 0:
            print(f"   Analyzing market {i+1}/{min(len(active_markets), 100)}...")

        analysis = analyze_market(market)
        if analysis.get("suitable"):
            score = score_market(market, analysis)
            scored_markets.append({
                "market": market,
                "analysis": analysis,
                "score": score
            })

    # Sort by score
    scored_markets.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n4. Found {len(scored_markets)} suitable markets")

    return scored_markets[:max_results]


def print_market_details(result: dict, rank: int):
    """Print detailed market information."""
    market = result["market"]
    analysis = result["analysis"]
    score = result["score"]

    print(f"\n{'='*70}")
    print(f"#{rank} SCORE: {score:.1f}")
    print(f"{'='*70}")
    print(f"Question: {market.get('question', 'N/A')[:70]}")
    print(f"Condition ID: {market.get('condition_id', 'N/A')}")
    print(f"End Date: {market.get('end_date_iso', 'N/A')}")

    print(f"\nOutcome A ({analysis['token_a']['outcome']}):")
    print(f"  Token ID: {analysis['token_a']['token_id'][:50]}...")
    print(f"  Bid: ${analysis['token_a']['best_bid']:.4f}  Ask: ${analysis['token_a']['best_ask']:.4f}  Spread: ${analysis['token_a']['spread']:.4f}")
    print(f"  Depth: {analysis['token_a']['depth']:.0f} shares")

    print(f"\nOutcome B ({analysis['token_b']['outcome']}):")
    print(f"  Token ID: {analysis['token_b']['token_id'][:50]}...")
    print(f"  Bid: ${analysis['token_b']['best_bid']:.4f}  Ask: ${analysis['token_b']['best_ask']:.4f}  Spread: ${analysis['token_b']['spread']:.4f}")
    print(f"  Depth: {analysis['token_b']['depth']:.0f} shares")

    print(f"\nMarket Summary:")
    print(f"  Price Sum: ${analysis['price_sum']:.4f} (should be ~$1.00)")
    print(f"  Total Depth: {analysis['total_depth']:.0f} shares")
    print(f"  Avg Spread: ${analysis['avg_spread']:.4f}")


def save_market_config(result: dict, filepath: str):
    """Save market configuration for paper trading."""
    market = result["market"]
    analysis = result["analysis"]

    config = {
        "question": market.get("question"),
        "condition_id": market.get("condition_id"),
        "end_date": market.get("end_date_iso"),
        "outcome_a": {
            "name": analysis["token_a"]["outcome"],
            "token_id": analysis["token_a"]["token_id"]
        },
        "outcome_b": {
            "name": analysis["token_b"]["outcome"],
            "token_id": analysis["token_b"]["token_id"]
        },
        "initial_prices": {
            "a_mid": analysis["token_a"]["mid"],
            "b_mid": analysis["token_b"]["mid"],
            "price_sum": analysis["price_sum"]
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "score": result["score"]
    }

    with open(filepath, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved market config to: {filepath}")
    return config


if __name__ == "__main__":
    print("=" * 70)
    print("POLYMARKET BINARY MARKET SCANNER")
    print("=" * 70)
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Scan for markets
    results = scan_for_markets(max_results=5)

    if not results:
        print("\nNo suitable markets found!")
        exit(1)

    # Print top markets
    print("\n" + "=" * 70)
    print("TOP MARKETS FOR MARKET MAKING")
    print("=" * 70)

    for i, result in enumerate(results, 1):
        print_market_details(result, i)

    # Save the best market
    best = results[0]
    config_path = "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/selected_market.json"
    save_market_config(best, config_path)

    print("\n" + "=" * 70)
    print("READY FOR PAPER TRADING")
    print("=" * 70)
    print(f"\nRun: python3 paper_trading/paper_trader.py")
