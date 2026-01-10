#!/usr/bin/env python3
"""
Find active BTC Up/Down 15-minute markets on Polymarket.

These markets run every 15 minutes during trading hours.
This script finds the current or next upcoming market.
"""
import requests
import json
from datetime import datetime, timezone
import time

GAMMA_API = "https://gamma-api.polymarket.com"


def get_btc_updown_markets(limit: int = 20) -> list:
    """Fetch recent BTC Up/Down markets from Gamma API."""

    # Search for BTC Up/Down markets
    params = {
        "limit": limit,
        "active": "true",
        "closed": "false",
        "order": "startDate",
        "ascending": "false",
        "tag": "crypto"
    }

    resp = requests.get(f"{GAMMA_API}/markets", params=params, timeout=30)
    markets = resp.json()

    # Filter for BTC Up/Down 15-minute markets
    btc_markets = []
    for m in markets:
        question = m.get("question", "").lower()
        if "bitcoin" in question and ("up or down" in question or "updown" in question):
            if "15" in question or "15m" in m.get("slug", ""):
                btc_markets.append(m)

    return btc_markets


def get_market_details(condition_id: str) -> dict:
    """Get full market details including token IDs."""
    resp = requests.get(f"{GAMMA_API}/markets/{condition_id}", timeout=30)
    return resp.json()


def parse_market_time(market: dict) -> dict:
    """Parse market timing from question or metadata."""
    question = market.get("question", "")

    # Extract time from question like "Bitcoin Up or Down - January 10, 3:00PM-3:15PM ET"
    # or from endDate field
    end_date = market.get("endDate")
    start_date = market.get("startDate")

    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    else:
        end_dt = None

    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    else:
        start_dt = None

    return {
        "question": question,
        "start": start_dt,
        "end": end_dt,
        "start_str": start_dt.strftime("%Y-%m-%d %H:%M:%S UTC") if start_dt else "Unknown",
        "end_str": end_dt.strftime("%Y-%m-%d %H:%M:%S UTC") if end_dt else "Unknown"
    }


def get_token_ids(market: dict) -> dict:
    """Extract token IDs for Up and Down outcomes."""
    tokens = market.get("tokens", [])

    result = {"up": None, "down": None}

    for token in tokens:
        outcome = token.get("outcome", "").lower()
        token_id = token.get("token_id")

        if "up" in outcome:
            result["up"] = token_id
        elif "down" in outcome:
            result["down"] = token_id

    return result


def find_active_market() -> dict:
    """Find the currently active or next upcoming BTC Up/Down market."""

    print("Searching for active BTC Up/Down markets...")
    markets = get_btc_updown_markets(limit=50)

    if not markets:
        print("No BTC Up/Down markets found. Trying alternative search...")
        # Try searching by slug pattern
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"limit": 100, "active": "true", "closed": "false"},
            timeout=30
        )
        all_markets = resp.json()

        for m in all_markets:
            slug = m.get("slug", "").lower()
            question = m.get("question", "").lower()
            if "btc-updown" in slug or ("bitcoin" in question and "up" in question and "down" in question):
                markets.append(m)

    print(f"Found {len(markets)} potential markets")

    now = datetime.now(timezone.utc)

    active_markets = []
    upcoming_markets = []

    for m in markets:
        timing = parse_market_time(m)
        token_ids = get_token_ids(m)

        # Skip if no token IDs
        if not token_ids["up"] or not token_ids["down"]:
            continue

        market_info = {
            "condition_id": m.get("conditionId"),
            "question": m.get("question"),
            "slug": m.get("slug"),
            "start": timing["start"],
            "end": timing["end"],
            "start_str": timing["start_str"],
            "end_str": timing["end_str"],
            "tokens": token_ids,
            "active": m.get("active"),
            "closed": m.get("closed"),
            "volume": m.get("volume", 0),
            "liquidity": m.get("liquidity", 0)
        }

        # Check if currently active
        if timing["start"] and timing["end"]:
            if timing["start"] <= now <= timing["end"]:
                active_markets.append(market_info)
            elif timing["start"] > now:
                upcoming_markets.append(market_info)
        elif m.get("active") and not m.get("closed"):
            active_markets.append(market_info)

    # Sort by start time
    active_markets.sort(key=lambda x: x["start"] or datetime.min.replace(tzinfo=timezone.utc))
    upcoming_markets.sort(key=lambda x: x["start"] or datetime.max.replace(tzinfo=timezone.utc))

    return {
        "timestamp": now.isoformat(),
        "active": active_markets,
        "upcoming": upcoming_markets[:5]  # Next 5 upcoming
    }


def search_by_slug_pattern():
    """Search for markets by common slug patterns."""
    patterns = [
        "btc-updown-15m",
        "bitcoin-up-or-down",
        "btc-up-down"
    ]

    all_found = []

    for pattern in patterns:
        try:
            resp = requests.get(
                f"{GAMMA_API}/markets",
                params={
                    "limit": 20,
                    "slug_contains": pattern,
                    "active": "true"
                },
                timeout=30
            )
            markets = resp.json()
            all_found.extend(markets)
        except:
            pass

    return all_found


def print_market_info(market: dict):
    """Print formatted market information."""
    print(f"\n{'='*70}")
    print(f"MARKET: {market['question']}")
    print(f"{'='*70}")
    print(f"  Condition ID: {market['condition_id']}")
    print(f"  Slug: {market['slug']}")
    print(f"  Start: {market['start_str']}")
    print(f"  End: {market['end_str']}")
    print(f"  Volume: ${market['volume']:,.2f}")
    print(f"  Liquidity: ${market['liquidity']:,.2f}")
    print(f"\n  Token IDs:")
    print(f"    Up:   {market['tokens']['up']}")
    print(f"    Down: {market['tokens']['down']}")


def save_market_config(market: dict, filepath: str):
    """Save market config for paper trading bot."""
    config = {
        "market_name": market["question"],
        "condition_id": market["condition_id"],
        "slug": market["slug"],
        "up_token": market["tokens"]["up"],
        "down_token": market["tokens"]["down"],
        "start_time": market["start"].isoformat() if market["start"] else None,
        "end_time": market["end"].isoformat() if market["end"] else None,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

    with open(filepath, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved market config to: {filepath}")
    return config


if __name__ == "__main__":
    print("="*70)
    print("BTC UP/DOWN MARKET FINDER")
    print("="*70)
    print(f"Current time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    result = find_active_market()

    if result["active"]:
        print(f"\n*** FOUND {len(result['active'])} ACTIVE MARKET(S) ***")
        for m in result["active"]:
            print_market_info(m)

        # Save the first active market
        best_market = result["active"][0]
        save_market_config(
            best_market,
            "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/active_market.json"
        )
    else:
        print("\nNo currently active markets found.")

    if result["upcoming"]:
        print(f"\n*** UPCOMING MARKETS ({len(result['upcoming'])}) ***")
        for m in result["upcoming"]:
            print_market_info(m)
            if m["start"]:
                time_until = m["start"] - datetime.now(timezone.utc)
                print(f"  Starts in: {time_until}")

        # If no active, save the next upcoming
        if not result["active"]:
            next_market = result["upcoming"][0]
            save_market_config(
                next_market,
                "/Users/mattiacostola/claude/prediction-arbitrage/paper_trading/next_market.json"
            )

    if not result["active"] and not result["upcoming"]:
        print("\nNo markets found. BTC Up/Down markets may not be running right now.")
        print("These markets typically run during US trading hours.")
        print("\nTrying alternative search methods...")

        # Try direct API search
        alt_markets = search_by_slug_pattern()
        if alt_markets:
            print(f"\nFound {len(alt_markets)} markets via alternative search:")
            for m in alt_markets[:5]:
                print(f"  - {m.get('question', 'Unknown')}")
                print(f"    Slug: {m.get('slug')}")
