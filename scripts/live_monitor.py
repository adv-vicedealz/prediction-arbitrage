#!/usr/bin/env python3
"""
Live monitor for Polymarket BTC Up/Down arbitrage opportunities.
Monitors the combined bid prices to detect when < $1.00
"""

import json
import urllib.request
import time
from datetime import datetime, timedelta
import sys

CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

def get_current_market():
    """Find the current active BTC Up/Down market."""
    now = datetime.utcnow()

    for i in range(-1, 6):
        market_end = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0) + timedelta(minutes=15 * (i + 1))
        ts = int(market_end.timestamp())
        slug = f"btc-updown-15m-{ts}"

        url = f"{GAMMA_API}/events?slug={slug}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                if data and not data[0].get('closed') and data[0].get('markets'):
                    market = data[0]['markets'][0]
                    if market.get('acceptingOrders'):
                        token_ids = json.loads(market.get('clobTokenIds', '[]'))
                        # Calculate market start time (15 min before end)
                        market_start = market_end - timedelta(minutes=15)
                        return {
                            'slug': slug,
                            'title': data[0].get('title'),
                            'up_token': token_ids[0] if len(token_ids) > 0 else None,
                            'down_token': token_ids[1] if len(token_ids) > 1 else None,
                            'start_time': market_start,
                            'end_time': market_end
                        }
        except:
            continue
    return None

def get_orderbook(token_id):
    """Fetch the orderbook for a token."""
    url = f"{CLOB_API}/book?token_id={token_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

def get_prices(up_token, down_token):
    """Get bid/ask prices for both tokens."""
    up_book = get_orderbook(up_token)
    down_book = get_orderbook(down_token)

    result = {'up_bid': None, 'up_ask': None, 'down_bid': None, 'down_ask': None,
              'up_bid_size': 0, 'down_bid_size': 0}

    if up_book:
        bids = up_book.get('bids', [])
        asks = up_book.get('asks', [])
        if bids:
            result['up_bid'] = float(bids[0]['price'])
            result['up_bid_size'] = float(bids[0]['size'])
        if asks:
            result['up_ask'] = float(asks[0]['price'])

    if down_book:
        bids = down_book.get('bids', [])
        asks = down_book.get('asks', [])
        if bids:
            result['down_bid'] = float(bids[0]['price'])
            result['down_bid_size'] = float(bids[0]['size'])
        if asks:
            result['down_ask'] = float(asks[0]['price'])

    return result

def monitor(duration_seconds=300, interval=2):
    """Monitor prices for arbitrage opportunities."""
    print("=" * 85)
    print("POLYMARKET BTC UP/DOWN - LIMIT ORDER ARBITRAGE MONITOR")
    print("=" * 85)

    market = get_current_market()
    if not market:
        print("ERROR: No active BTC Up/Down market found!")
        return

    now = datetime.utcnow()
    time_to_start = (market['start_time'] - now).total_seconds() / 60
    time_to_end = (market['end_time'] - now).total_seconds() / 60

    print(f"\nMarket: {market['title']}")
    print(f"Window: {market['start_time'].strftime('%H:%M')} - {market['end_time'].strftime('%H:%M')} UTC")
    print(f"Status: {'IN WINDOW' if time_to_start <= 0 else f'Starts in {time_to_start:.1f} min'}")
    print(f"Time to resolution: {time_to_end:.1f} min")
    print("\n" + "=" * 85)
    print(f"{'Time':8} | {'UP Bid':10} | {'DOWN Bid':10} | {'Combined':10} | {'Spread':10} | Status")
    print("-" * 85)

    start_time = time.time()
    all_data = []
    opportunities = []

    while time.time() - start_time < duration_seconds:
        try:
            prices = get_prices(market['up_token'], market['down_token'])
            now_str = datetime.utcnow().strftime('%H:%M:%S')

            up_bid = prices['up_bid']
            down_bid = prices['down_bid']

            if up_bid and down_bid:
                combined = up_bid + down_bid
                spread = 1.0 - combined

                data_point = {
                    'time': now_str,
                    'up_bid': up_bid,
                    'down_bid': down_bid,
                    'combined': combined,
                    'spread': spread
                }
                all_data.append(data_point)

                # Format sizes
                up_size = f"({prices['up_bid_size']:,.0f})" if prices['up_bid_size'] > 0 else ""
                down_size = f"({prices['down_bid_size']:,.0f})" if prices['down_bid_size'] > 0 else ""

                if combined < 0.995:  # Below 99.5 cents is meaningful
                    status = f"*** ARBIT +${spread:.4f} ***"
                    opportunities.append(data_point)
                elif combined < 1.0:
                    status = f"ARBIT +${spread:.4f}"
                    opportunities.append(data_point)
                elif combined == 1.0:
                    status = "BREAK-EVEN"
                else:
                    status = f"LOSS -${-spread:.4f}"

                print(f"{now_str:8} | ${up_bid:<4.3f} {up_size:<5} | ${down_bid:<4.3f} {down_size:<5} | ${combined:<9.4f} | ${spread:+.4f}   | {status}")
            else:
                print(f"{now_str:8} | {'N/A':10} | {'N/A':10} | {'N/A':10} | {'N/A':10} | No orderbook")

            # Check if market changed
            if datetime.utcnow() > market['end_time']:
                print("\n*** Market ended ***")
                market = get_current_market()
                if market:
                    print(f"Switched to: {market['title']}")
                else:
                    break

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nStopped by user.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(interval)

    # Summary
    print("\n" + "=" * 85)
    print("SUMMARY")
    print("=" * 85)
    print(f"Monitoring duration: {time.time() - start_time:.0f} seconds")
    print(f"Data points collected: {len(all_data)}")

    if all_data:
        spreads = [d['spread'] for d in all_data]
        print(f"\nCombined Bid Price:")
        print(f"  Min: ${1-max(spreads):.4f}")
        print(f"  Max: ${1-min(spreads):.4f}")
        print(f"  Avg: ${1-sum(spreads)/len(spreads):.4f}")

    if opportunities:
        print(f"\nArbitrage Opportunities (combined < $1.00):")
        print(f"  Count: {len(opportunities)} ({len(opportunities)/len(all_data)*100:.1f}% of time)")
        opp_spreads = [o['spread'] for o in opportunities]
        print(f"  Best spread: ${max(opp_spreads):.4f}")
        print(f"  Avg spread: ${sum(opp_spreads)/len(opp_spreads):.4f}")
    else:
        print("\nNo arbitrage opportunities detected during monitoring period.")

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    monitor(duration_seconds=duration, interval=2)
