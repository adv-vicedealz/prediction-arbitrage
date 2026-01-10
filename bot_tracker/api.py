"""
FastAPI REST endpoints for the bot tracker dashboard.
"""

from typing import List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import TARGET_WALLETS, MARKET_SLUGS_PATTERN, BUY_ONLY
from .models import (
    WalletPosition,
    MarketContext,
    TradeEvent,
    TimingPattern,
    PricePattern,
    HedgePattern,
    TrackerState
)

# Create FastAPI app
app = FastAPI(
    title="Bot Trading Tracker API",
    description="Real-time bot trading analysis for Polymarket",
    version="0.1.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# These will be injected by main.py
position_tracker = None
pattern_detector = None
market_fetcher = None
ws_server = None
start_time = None
trade_history: List[TradeEvent] = []


def set_dependencies(pos_tracker, pat_detector, mkt_fetcher, websocket_server, start):
    """Inject dependencies from main.py."""
    global position_tracker, pattern_detector, market_fetcher, ws_server, start_time
    position_tracker = pos_tracker
    pattern_detector = pat_detector
    market_fetcher = mkt_fetcher
    ws_server = websocket_server
    start_time = start


def add_trade_to_history(trade: TradeEvent):
    """Add a trade to the history (called from main.py)."""
    global trade_history
    trade_history.insert(0, trade)
    # Keep only last 2000 trades
    if len(trade_history) > 2000:
        trade_history = trade_history[:2000]


# ===== Status Endpoints =====

# Check if dashboard is built
_dashboard_dist = Path(__file__).parent / "dashboard" / "dist"
_dashboard_available = _dashboard_dist.exists()

@app.get("/")
def root():
    """Root endpoint - serve dashboard if available, otherwise API info."""
    if _dashboard_available:
        return FileResponse(_dashboard_dist / "index.html")
    return {
        "name": "Bot Trading Tracker API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/status", response_model=TrackerState)
def get_status():
    """Get current tracker status."""
    uptime = 0
    if start_time:
        uptime = (datetime.now() - start_time).total_seconds()

    last_trade_ts = None
    if trade_history:
        last_trade_ts = trade_history[0].timestamp

    return TrackerState(
        connected_clients=ws_server.get_client_count() if ws_server else 0,
        tracked_wallets=len(TARGET_WALLETS),
        active_markets=len(market_fetcher.cache) if market_fetcher else 0,
        total_trades_seen=len(trade_history),
        last_trade_ts=last_trade_ts,
        uptime_seconds=uptime
    )


# ===== Wallet Endpoints =====

@app.get("/api/wallets")
def get_wallets():
    """Get list of tracked wallets."""
    return [
        {"address": addr, "name": name}
        for addr, name in TARGET_WALLETS.items()
    ]


@app.get("/api/wallets/{wallet}/positions", response_model=List[WalletPosition])
def get_wallet_positions(wallet: str):
    """Get all positions for a specific wallet."""
    if not position_tracker:
        raise HTTPException(status_code=503, detail="Position tracker not initialized")

    positions = position_tracker.get_wallet_positions(wallet)
    if not positions:
        return []
    return positions


@app.get("/api/wallets/{wallet}/trades", response_model=List[TradeEvent])
def get_wallet_trades(wallet: str, limit: int = 50):
    """Get recent trades for a specific wallet."""
    wallet = wallet.lower()
    wallet_trades = [t for t in trade_history if t.wallet.lower() == wallet]
    return wallet_trades[:limit]


# ===== Position Endpoints =====

@app.get("/api/positions", response_model=List[WalletPosition])
def get_all_positions():
    """Get all current positions."""
    if not position_tracker:
        raise HTTPException(status_code=503, detail="Position tracker not initialized")
    return position_tracker.get_all_positions()


@app.get("/api/positions/{wallet}/{market_slug}", response_model=Optional[WalletPosition])
def get_position(wallet: str, market_slug: str):
    """Get position for a specific wallet and market."""
    if not position_tracker:
        raise HTTPException(status_code=503, detail="Position tracker not initialized")

    position = position_tracker.get_position(wallet, market_slug)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position


# ===== Market Endpoints =====

@app.get("/api/markets")
def get_markets():
    """Get all tracked markets."""
    if not market_fetcher:
        raise HTTPException(status_code=503, detail="Market fetcher not initialized")

    return [
        {
            "slug": m.slug,
            "question": m.question,
            "time_to_resolution_mins": m.time_to_resolution_mins,
            "resolved": m.resolved,
            "winning_outcome": m.winning_outcome,
            "up_best_bid": m.up_best_bid,
            "down_best_bid": m.down_best_bid,
            "combined_bid": m.combined_bid,
            "spread": m.spread
        }
        for m in market_fetcher.cache.values()
    ]


@app.get("/api/markets/active", response_model=List[MarketContext])
def get_active_markets():
    """Get currently active (non-resolved) markets."""
    if not market_fetcher:
        raise HTTPException(status_code=503, detail="Market fetcher not initialized")
    return market_fetcher.get_active_markets()


@app.get("/api/markets/{slug}", response_model=Optional[MarketContext])
def get_market(slug: str):
    """Get market context by slug."""
    if not market_fetcher:
        raise HTTPException(status_code=503, detail="Market fetcher not initialized")

    market = market_fetcher.cache.get(slug)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


@app.get("/api/markets/{slug}/positions", response_model=List[WalletPosition])
def get_market_positions(slug: str):
    """Get all positions for a specific market."""
    if not position_tracker:
        raise HTTPException(status_code=503, detail="Position tracker not initialized")
    return position_tracker.get_market_positions(slug)


# ===== Trade Endpoints =====

@app.get("/api/trades", response_model=List[TradeEvent])
def get_recent_trades(limit: int = 500):
    """Get recent trades across all wallets."""
    return trade_history[:limit]


@app.get("/api/trades/{market_slug}", response_model=List[TradeEvent])
def get_market_trades(market_slug: str, limit: int = 100):
    """Get recent trades for a specific market."""
    market_trades = [t for t in trade_history if t.market_slug == market_slug]
    return market_trades[:limit]


# ===== Pattern Endpoints =====

@app.get("/api/patterns/{wallet}/{market_slug}")
def get_patterns(wallet: str, market_slug: str):
    """Get pattern analysis for a wallet in a market."""
    if not pattern_detector or not position_tracker:
        raise HTTPException(status_code=503, detail="Pattern detector not initialized")

    position = position_tracker.get_position(wallet, market_slug)
    market = market_fetcher.cache.get(market_slug) if market_fetcher else None

    return pattern_detector.get_full_analysis(wallet, market_slug, position, market)


@app.get("/api/patterns/{wallet}/{market_slug}/timing", response_model=Optional[TimingPattern])
def get_timing_pattern(wallet: str, market_slug: str):
    """Get timing pattern for a wallet in a market."""
    if not pattern_detector:
        raise HTTPException(status_code=503, detail="Pattern detector not initialized")

    market = market_fetcher.cache.get(market_slug) if market_fetcher else None
    return pattern_detector.analyze_timing(wallet, market_slug, market)


@app.get("/api/patterns/{wallet}/{market_slug}/price", response_model=Optional[PricePattern])
def get_price_pattern(wallet: str, market_slug: str):
    """Get price pattern for a wallet in a market."""
    if not pattern_detector:
        raise HTTPException(status_code=503, detail="Pattern detector not initialized")
    return pattern_detector.analyze_price(wallet, market_slug)


@app.get("/api/patterns/{wallet}/{market_slug}/hedge", response_model=Optional[HedgePattern])
def get_hedge_pattern(wallet: str, market_slug: str):
    """Get hedge pattern for a wallet in a market."""
    if not pattern_detector or not position_tracker:
        raise HTTPException(status_code=503, detail="Pattern detector not initialized")

    position = position_tracker.get_position(wallet, market_slug)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return pattern_detector.analyze_hedge(position)


# ===== Summary Endpoints =====

@app.get("/api/summary")
def get_summary():
    """Get overall summary statistics."""
    summary = {
        "wallets": len(TARGET_WALLETS),
        "trades": len(trade_history),
        "positions": 0,
        "markets": 0,
        "connected_clients": 0
    }

    if position_tracker:
        pos_summary = position_tracker.get_summary()
        summary["positions"] = pos_summary.get("total_positions", 0)
        summary["markets"] = pos_summary.get("total_markets", 0)

    if ws_server:
        summary["connected_clients"] = ws_server.get_client_count()

    return summary


@app.get("/api/tracking-info")
def get_tracking_info():
    """Get tracking session info including coverage per market."""
    info = {
        "tracking_started": start_time.isoformat() if start_time else None,
        "uptime_seconds": (datetime.now() - start_time).total_seconds() if start_time else 0,
        "total_trades_captured": len(trade_history),
        "markets": []
    }

    if not trade_history:
        return info

    # Group trades by market
    market_trades = {}
    for trade in trade_history:
        slug = trade.market_slug
        if slug not in market_trades:
            market_trades[slug] = []
        market_trades[slug].append(trade)

    # Analyze each market
    for slug, trades in market_trades.items():
        trades_sorted = sorted(trades, key=lambda t: t.timestamp)
        first_trade = trades_sorted[0]
        last_trade = trades_sorted[-1]

        # Get market context if available
        market_context = market_fetcher.cache.get(slug) if market_fetcher else None

        market_info = {
            "slug": slug,
            "question": first_trade.market_question,
            "trades_captured": len(trades),
            "first_trade_time": datetime.fromtimestamp(first_trade.timestamp).isoformat(),
            "last_trade_time": datetime.fromtimestamp(last_trade.timestamp).isoformat(),
            "tracking_duration_mins": (last_trade.timestamp - first_trade.timestamp) / 60,
        }

        # Add market timing if available
        if market_context:
            market_info["market_end_time"] = market_context.end_date.isoformat() if market_context.end_date else None
            market_info["resolved"] = market_context.resolved
            market_info["winning_outcome"] = market_context.winning_outcome

            # Calculate if we caught the full event
            if market_context.end_date:
                market_end_ts = market_context.end_date.timestamp()
                tracking_start_ts = start_time.timestamp() if start_time else first_trade.timestamp

                # Did we start before market end?
                if tracking_start_ts < market_end_ts:
                    market_info["tracking_coverage"] = "partial_or_full"
                    # How much of the market duration did we track?
                    market_duration = 15 * 60  # 15 min markets
                    tracked_duration = min(market_end_ts, last_trade.timestamp) - first_trade.timestamp
                    market_info["coverage_percent"] = min(100, (tracked_duration / market_duration) * 100)
                else:
                    market_info["tracking_coverage"] = "started_after_end"
                    market_info["coverage_percent"] = 0
            else:
                market_info["tracking_coverage"] = "unknown"

        info["markets"].append(market_info)

    return info


# ===== Configuration Endpoints =====

class WalletConfig(BaseModel):
    address: str
    name: str = "CustomWallet"

class TrackerConfig(BaseModel):
    running: bool

# Store mutable config
tracker_config = {
    "wallet_address": list(TARGET_WALLETS.keys())[0] if TARGET_WALLETS else "",
    "wallet_name": list(TARGET_WALLETS.values())[0] if TARGET_WALLETS else "",
    "market_filter": MARKET_SLUGS_PATTERN,
    "buy_only": BUY_ONLY,
    "running": True
}

# Reference to trade poller for control
trade_poller = None

def set_trade_poller(poller):
    """Set reference to trade poller for start/stop control."""
    global trade_poller
    trade_poller = poller


@app.get("/api/config")
def get_config():
    """Get current tracker configuration."""
    return {
        "wallet": {
            "address": tracker_config["wallet_address"],
            "name": tracker_config["wallet_name"]
        },
        "market_filter": tracker_config["market_filter"],
        "buy_only": tracker_config["buy_only"],
        "running": tracker_config["running"]
    }


@app.post("/api/config/wallet")
def set_wallet(config: WalletConfig):
    """Update the tracked wallet."""
    tracker_config["wallet_address"] = config.address.lower()
    tracker_config["wallet_name"] = config.name

    # Update TARGET_WALLETS in config module
    TARGET_WALLETS.clear()
    TARGET_WALLETS[config.address.lower()] = config.name

    return {"success": True, "wallet": config}


@app.post("/api/tracker/start")
def start_tracker():
    """Start the trade poller."""
    if trade_poller:
        trade_poller.running = True
        tracker_config["running"] = True
        return {"success": True, "running": True}
    raise HTTPException(status_code=503, detail="Trade poller not available")


@app.post("/api/tracker/stop")
def stop_tracker():
    """Stop the trade poller."""
    if trade_poller:
        trade_poller.running = False
        tracker_config["running"] = False
        return {"success": True, "running": False}
    raise HTTPException(status_code=503, detail="Trade poller not available")


@app.post("/api/tracker/toggle")
def toggle_tracker():
    """Toggle the trade poller on/off."""
    if trade_poller:
        trade_poller.running = not trade_poller.running
        tracker_config["running"] = trade_poller.running
        return {"success": True, "running": trade_poller.running}
    raise HTTPException(status_code=503, detail="Trade poller not available")


# ===== Dashboard Static Files =====

# Mount static files for dashboard (if built)
if _dashboard_available:
    app.mount("/assets", StaticFiles(directory=_dashboard_dist / "assets"), name="assets")
