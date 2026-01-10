#!/usr/bin/env python3
"""
Simple test script to verify the tracker is working.
Run: python -m bot_tracker.test_tracker
"""

import asyncio
import aiohttp
from datetime import datetime

from .config import POLYMARKET_DATA_API, TARGET_WALLETS, MARKET_SLUGS_PATTERN
import re


async def test_trades_api():
    """Test fetching trades from Polymarket API."""
    print("=" * 60)
    print("TESTING POLYMARKET TRADES API")
    print("=" * 60)
    print()

    async with aiohttp.ClientSession() as session:
        for wallet, name in TARGET_WALLETS.items():
            print(f"Wallet: {name} ({wallet[:10]}...{wallet[-6:]})")
            print("-" * 40)

            # Fetch recent BUY trades
            params = {
                "user": wallet,
                "limit": 20,
                "side": "BUY"
            }

            try:
                async with session.get(
                    f"{POLYMARKET_DATA_API}/trades",
                    params=params
                ) as resp:
                    if resp.status == 200:
                        trades = await resp.json()
                        print(f"Total trades returned: {len(trades)}")
                        print()

                        # Filter to BTC/ETH 15-min markets
                        filtered = [
                            t for t in trades
                            if re.match(MARKET_SLUGS_PATTERN, t.get("slug", ""))
                        ]
                        print(f"BTC/ETH 15-min trades: {len(filtered)}")
                        print()

                        if filtered:
                            print(f"{'Time':<20} {'Side':<5} {'Outcome':<6} {'Size':>10} {'Price':>8} {'Market'}")
                            print("-" * 80)

                            for t in filtered[:10]:
                                ts = t.get("timestamp", "")
                                if isinstance(ts, str):
                                    try:
                                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                                    except:
                                        time_str = ts[:19]
                                else:
                                    time_str = str(ts)

                                print(
                                    f"{time_str:<20} "
                                    f"{t.get('side', ''):<5} "
                                    f"{t.get('outcome', ''):<6} "
                                    f"{float(t.get('size', 0)):>10.2f} "
                                    f"${float(t.get('price', 0)):>7.3f} "
                                    f"{t.get('slug', '')[:30]}"
                                )
                        else:
                            print("No BTC/ETH 15-min trades found.")

                    else:
                        print(f"Error: {resp.status}")
                        text = await resp.text()
                        print(f"Response: {text[:200]}")

            except Exception as e:
                print(f"Error: {e}")

            print()


async def test_positions_api():
    """Test fetching positions from Polymarket API."""
    print("=" * 60)
    print("TESTING POLYMARKET POSITIONS API")
    print("=" * 60)
    print()

    async with aiohttp.ClientSession() as session:
        for wallet, name in TARGET_WALLETS.items():
            print(f"Wallet: {name} ({wallet[:10]}...{wallet[-6:]})")
            print("-" * 40)

            params = {
                "user": wallet,
                "limit": 20,
            }

            try:
                async with session.get(
                    f"{POLYMARKET_DATA_API}/positions",
                    params=params
                ) as resp:
                    if resp.status == 200:
                        positions = await resp.json()
                        print(f"Total positions: {len(positions)}")
                        print()

                        # Filter to BTC/ETH 15-min markets
                        filtered = [
                            p for p in positions
                            if re.match(MARKET_SLUGS_PATTERN, p.get("slug", ""))
                        ]
                        print(f"BTC/ETH 15-min positions: {len(filtered)}")
                        print()

                        if filtered:
                            print(f"{'Outcome':<8} {'Size':>10} {'Avg Price':>10} {'P&L':>12} {'Market'}")
                            print("-" * 70)

                            for p in filtered[:10]:
                                print(
                                    f"{p.get('outcome', ''):<8} "
                                    f"{float(p.get('size', 0)):>10.2f} "
                                    f"${float(p.get('avgPrice', 0)):>9.3f} "
                                    f"${float(p.get('cashPnl', 0)):>11.2f} "
                                    f"{p.get('slug', '')[:30]}"
                                )
                        else:
                            print("No BTC/ETH 15-min positions found.")

                    else:
                        print(f"Error: {resp.status}")

            except Exception as e:
                print(f"Error: {e}")

            print()


async def main():
    """Run all tests."""
    await test_trades_api()
    await test_positions_api()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print("If you see trades above, the tracker can fetch data!")
    print()
    print("To run the full tracker:")
    print("  python -m bot_tracker.main")
    print()


if __name__ == "__main__":
    asyncio.run(main())
