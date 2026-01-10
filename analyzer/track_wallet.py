"""
Track @gabagool22 trades on Polymarket
Sends Telegram notification when they trade
"""

import time
import requests
from web3 import Web3

# ============ CONFIGURATION ============

# Target wallet (@gabagool22)
TARGET_WALLET = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d".lower()
TARGET_NAME = "gabagool22"

# Polygon RPC (free, public)
POLYGON_RPC = "https://polygon-rpc.com"

# Polymarket contracts
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEG_RISK_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"

POLYMARKET_CONTRACTS = {
    CTF_EXCHANGE.lower(),
    NEG_RISK_EXCHANGE.lower()
}

# Telegram (fill these in)
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"  # Get from @BotFather
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"      # Get from @userinfobot

# Polling interval (seconds)
POLL_INTERVAL = 3


# ============ TELEGRAM ============

def send_telegram(message: str):
    """Send alert to Telegram"""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("[Telegram not configured - printing only]")
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=10
        )
    except Exception as e:
        print(f"Telegram error: {e}")


# ============ POLYMARKET API ============

def get_market_info(token_id: str) -> dict:
    """Get market details from Gamma API"""
    try:
        resp = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"clob_token_ids": token_id},
            timeout=10
        )
        markets = resp.json()
        return markets[0] if markets else {}
    except:
        return {}


def get_price(token_id: str) -> str:
    """Get current price"""
    try:
        resp = requests.get(
            "https://clob.polymarket.com/midpoint",
            params={"token_id": token_id},
            timeout=5
        )
        mid = resp.json().get("mid", "?")
        return f"{float(mid):.1%}" if mid != "?" else "?"
    except:
        return "?"


# ============ EVENT DECODING ============

# OrderFilled event ABI
ORDER_FILLED_ABI = [{
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "maker", "type": "address"},
        {"indexed": False, "name": "taker", "type": "address"},
        {"indexed": False, "name": "makerAssetId", "type": "uint256"},
        {"indexed": False, "name": "takerAssetId", "type": "uint256"},
        {"indexed": False, "name": "makerAmountFilled", "type": "uint256"},
        {"indexed": False, "name": "takerAmountFilled", "type": "uint256"}
    ],
    "name": "OrderFilled",
    "type": "event"
}]


def process_trade(event, contract_address: str) -> dict:
    """Extract trade info from event"""
    return {
        "maker": event.args.maker.lower(),
        "taker": event.args.taker.lower() if hasattr(event.args, 'taker') else None,
        "token_id": str(event.args.takerAssetId),
        "amount_usdc": event.args.makerAmountFilled / 1e6,
        "shares": event.args.takerAmountFilled / 1e6,
        "contract": "CTF" if contract_address.lower() == CTF_EXCHANGE.lower() else "NegRisk"
    }


# ============ MAIN MONITOR ============

def format_alert(trade: dict, market: dict) -> str:
    """Format trade alert message"""
    price = get_price(trade["token_id"])

    return f"""
🚨 <b>@{TARGET_NAME} TRADED!</b>

💰 Amount: <b>${trade['amount_usdc']:,.2f}</b>
📦 Shares: {trade['shares']:,.0f}

📊 Market: {market.get('question', 'Unknown')[:80]}
📈 Price: {price}
🏷️ Category: {market.get('category', '?')}

🔗 <a href="https://polymarket.com/event/{market.get('slug', '')}">View Market</a>
👤 <a href="https://polymarket.com/@{TARGET_NAME}">View Profile</a>
"""


def monitor():
    """Main monitoring loop"""

    print(f"🎯 Tracking: @{TARGET_NAME}")
    print(f"👛 Wallet: {TARGET_WALLET[:10]}...{TARGET_WALLET[-6:]}")
    print(f"⏱️  Polling every {POLL_INTERVAL} seconds")
    print()
    print("Waiting for trades...")
    print("-" * 50)

    # Connect to Polygon
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

    if not w3.is_connected():
        print("❌ Failed to connect to Polygon RPC")
        return

    print(f"✅ Connected to Polygon (block: {w3.eth.block_number})")

    # Create contract instances
    ctf_contract = w3.eth.contract(
        address=Web3.to_checksum_address(CTF_EXCHANGE),
        abi=ORDER_FILLED_ABI
    )

    neg_risk_contract = w3.eth.contract(
        address=Web3.to_checksum_address(NEG_RISK_EXCHANGE),
        abi=ORDER_FILLED_ABI
    )

    # Start from current block
    last_block = w3.eth.block_number
    trades_detected = 0

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                # Check both contracts for OrderFilled events
                for contract, name in [(ctf_contract, "CTF"), (neg_risk_contract, "NegRisk")]:
                    try:
                        events = contract.events.OrderFilled.get_logs(
                            fromBlock=last_block + 1,
                            toBlock=current_block
                        )

                        for event in events:
                            maker = event.args.maker.lower()

                            # Check if our target wallet
                            if maker == TARGET_WALLET:
                                trades_detected += 1
                                trade = process_trade(event, contract.address)
                                market = get_market_info(trade["token_id"])

                                # Format and send alert
                                message = format_alert(trade, market)
                                print(message)
                                send_telegram(message)

                    except Exception as e:
                        if "429" in str(e):
                            print("Rate limited, waiting...")
                            time.sleep(5)

                last_block = current_block

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n\nStopped. Detected {trades_detected} trades.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)


# ============ RUN ============

if __name__ == "__main__":
    monitor()
