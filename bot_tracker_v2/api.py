"""
FastAPI server with WebSocket support.
All endpoints the React dashboard needs.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import TARGET_WALLETS
from .database import Database
from .services.prices import PriceStream
from .scheduler import Scheduler
from .logger import setup_logger

log = setup_logger(__name__)


# =============================================================================
# APP SETUP
# =============================================================================

app = FastAPI(
    title="Bot Tracker v2",
    description="Tracks trades from target wallets on Polymarket",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# GLOBAL REFERENCES (set by main.py)
# =============================================================================

db: Optional[Database] = None
prices: Optional[PriceStream] = None
scheduler: Optional[Scheduler] = None
start_time: Optional[datetime] = None
running: bool = True


def set_dependencies(
    database: Database,
    price_stream: PriceStream,
    task_scheduler: Scheduler,
    app_start_time: datetime
):
    """Set global dependencies from main."""
    global db, prices, scheduler, start_time
    db = database
    prices = price_stream
    scheduler = task_scheduler
    start_time = app_start_time


# =============================================================================
# WEBSOCKET MANAGER
# =============================================================================

class WebSocketManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.sequence = 0

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)
        log.info(f"WebSocket client connected (total: {len(self.connections)})")

        # Send connected message
        await self.send(ws, "connected", {})

    def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)
        log.info(f"WebSocket client disconnected (total: {len(self.connections)})")

    async def send(self, ws: WebSocket, msg_type: str, data: dict):
        """Send message to single client."""
        self.sequence += 1
        message = {
            "type": msg_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sequence": self.sequence
        }
        try:
            await ws.send_json(message)
        except Exception:
            self.disconnect(ws)

    async def broadcast(self, msg_type: str, data: dict):
        """Broadcast to all connected clients."""
        if not self.connections:
            return

        self.sequence += 1
        message = {
            "type": msg_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sequence": self.sequence
        }

        disconnected = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.connections.discard(ws)

    def get_count(self) -> int:
        return len(self.connections)


ws_manager = WebSocketManager()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class WalletUpdate(BaseModel):
    address: str
    name: str


class TraderCreate(BaseModel):
    wallet: str
    name: str
    link: str = ""
    all_time_profit: float = 0


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/config")
def get_config():
    """Get tracker configuration."""
    wallets = db.get_wallets() if db else []
    wallet = wallets[0] if wallets else {"address": "", "name": ""}

    return {
        "wallet": wallet,
        "market_filter": "",
        "buy_only": False,
        "running": running
    }


@app.get("/api/wallets")
def get_wallets():
    """Get tracked wallets."""
    if not db:
        return []
    return db.get_wallets()


@app.get("/api/trades")
def get_trades(limit: int = Query(2000, le=10000)):
    """Get recent trades."""
    if not db:
        return []

    trades = db.get_trades(limit=limit)

    # Format for frontend
    result = []
    for t in trades:
        result.append({
            "id": t["id"],
            "tx_hash": t.get("tx_hash", ""),
            "timestamp": t["timestamp"],
            "wallet": t["wallet"],
            "wallet_name": t.get("wallet_name", ""),
            "role": t.get("role", "taker"),  # maker or taker
            "side": t["side"],  # BUY or SELL
            "outcome": t["outcome"],  # Up or Down
            "shares": t["shares"],
            "usdc": t.get("usdc", t["shares"] * t["price"]),
            "price": t["price"],
            "fee": t.get("fee", 0),  # Fee stored for reference
            "market_slug": t["market_slug"],
            "market_question": ""
        })

    return result


@app.get("/api/positions")
def get_positions():
    """Get computed positions."""
    if not db:
        return []
    return db.get_positions()


@app.get("/api/prices")
def get_prices(limit: int = Query(50, le=1000)):
    """Get recent prices."""
    if not db:
        return []
    return db.get_prices(limit=limit)


@app.get("/api/prices/by-market")
def get_prices_by_market():
    """Get price counts per market."""
    if not db:
        return {}
    return db.get_price_counts_by_market()


@app.get("/api/price-stream/status")
def get_price_stream_status():
    """Get price stream status."""
    if not prices:
        return {
            "connected": False,
            "running": False,
            "subscribed_assets": 0,
            "assets": []
        }
    return prices.get_status()


@app.get("/api/tracking-info")
def get_tracking_info():
    """Get tracking info for dashboard."""
    if not db or not start_time:
        return {
            "tracking_started": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": 0,
            "total_trades_captured": 0,
            "markets": []
        }
    return db.get_tracking_info(start_time)


@app.get("/api/traders")
def get_traders():
    """Get top traders list."""
    if not db:
        return []
    return db.get_traders()


@app.post("/api/traders")
def add_trader(trader: TraderCreate):
    """Add a trader."""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    db.save_trader({
        "wallet": trader.wallet,
        "name": trader.name,
        "link": trader.link,
        "all_time_profit": trader.all_time_profit
    })
    return {"success": True}


@app.delete("/api/traders/{wallet}")
def delete_trader(wallet: str):
    """Delete a trader."""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    deleted = db.delete_trader(wallet)
    return {"success": deleted}


@app.post("/api/tracker/toggle")
def toggle_tracker():
    """Toggle tracker running state."""
    global running
    running = not running
    return {"running": running}


@app.post("/api/config/wallet")
def update_wallet(wallet: WalletUpdate):
    """Update tracked wallet."""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    db.update_wallet(wallet.address, wallet.name)
    return {"success": True}


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@app.get("/api/analytics/summary")
def get_analytics_summary(wallet: Optional[str] = None):
    """Get aggregated analytics summary for resolved markets."""
    if not db:
        return {
            "total_pnl": 0, "win_rate": 0, "total_markets": 0,
            "winning_markets": 0, "losing_markets": 0, "total_volume": 0,
            "effective_edge": 0, "profit_factor": 0, "avg_win": 0, "avg_loss": 0,
            "avg_maker_ratio": 0, "btc_pnl": 0, "eth_pnl": 0, "btc_markets": 0, "eth_markets": 0
        }
    return db.get_analytics_summary(wallet)


@app.get("/api/analytics/markets")
def get_markets_analytics(wallet: Optional[str] = None, asset: Optional[str] = None):
    """Get per-market analytics for resolved markets."""
    if not db:
        return []
    return db.get_markets_analytics(wallet, asset)


@app.get("/api/analytics/pnl-timeline")
def get_pnl_timeline(wallet: Optional[str] = None):
    """Get cumulative P&L by market end time."""
    if not db:
        return []
    return db.get_pnl_over_time(wallet)


@app.get("/api/analytics/market/{slug:path}/trades")
def get_market_trades(slug: str):
    """Get trades for a specific market with running position totals."""
    if not db:
        return []
    return db.get_market_trades_timeline(slug)


@app.get("/api/analytics/price-execution")
def get_price_execution(wallet: Optional[str] = None):
    """Analyze trade execution prices vs market prices."""
    if not db:
        return {
            "total_trades": 0, "trades_with_price_data": 0,
            "avg_spread_captured": 0, "pct_at_bid": 0, "pct_at_ask": 0,
            "pct_between": 0, "avg_combined_cost": 0, "pct_below_dollar": 0,
            "combined_cost_distribution": [], "markets_analyzed": 0, "order_placement_analysis": []
        }
    return db.get_price_execution_analysis(wallet)


# =============================================================================
# DEBUG/ADMIN ENDPOINTS
# =============================================================================

@app.get("/api/scheduler/status")
def get_scheduler_status():
    """Get scheduler status (for debugging)."""
    if not scheduler:
        return {"running": False}
    return scheduler.get_stats()


@app.get("/api/markets")
def get_markets():
    """Get all markets (for debugging)."""
    if not db:
        return []

    with db._get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM markets ORDER BY end_time DESC LIMIT 100"
        ).fetchall()
        return [dict(row) for row in rows]


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "running": running
    }


# =============================================================================
# WEBSOCKET
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await ws_manager.connect(ws)

    try:
        while True:
            # Wait for client messages (mostly just keepalive)
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30)
                # Echo ping/pong for keepalive
                if data == "ping":
                    await ws_manager.send(ws, "ping", {})
            except asyncio.TimeoutError:
                # Send keepalive ping
                await ws_manager.send(ws, "ping", {})
            except WebSocketDisconnect:
                break

    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(ws)


# =============================================================================
# BROADCAST HELPERS
# =============================================================================

async def broadcast_trade(trade: dict):
    """Broadcast new trade to all clients."""
    await ws_manager.broadcast("trade", trade)


async def broadcast_position(position: dict):
    """Broadcast position update to all clients."""
    await ws_manager.broadcast("position", position)


async def broadcast_stats():
    """Broadcast current stats."""
    if not db:
        return

    positions = db.get_positions()
    trade_count = db.get_trade_count()
    wallets = db.get_wallets()

    stats = {
        "total_wallets": len(wallets),
        "total_markets": len(set(p["market_slug"] for p in positions)),
        "total_positions": len(positions),
        "total_trades": trade_count,
        "connected_clients": ws_manager.get_count()
    }

    await ws_manager.broadcast("stats", stats)


# =============================================================================
# STATIC FILE SERVING (for production)
# =============================================================================

STATIC_DIR = Path(__file__).parent.parent / "static"


def setup_static_files():
    """Mount static files if they exist (production mode)."""
    if STATIC_DIR.exists():
        log.info(f"Serving static files from {STATIC_DIR}")
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/")
        async def serve_index():
            return FileResponse(STATIC_DIR / "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # Serve static file if exists, otherwise serve index.html (SPA)
            file_path = STATIC_DIR / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(STATIC_DIR / "index.html")


# Setup static files on module load
setup_static_files()
