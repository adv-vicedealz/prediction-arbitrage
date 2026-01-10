"""
WebSocket server for real-time updates to dashboard.
"""

import asyncio
import json
from typing import Set, Any
from datetime import datetime

try:
    import websockets
    from websockets.server import serve, WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Warning: websockets not installed. Run: pip install websockets")

from .config import WEBSOCKET_HOST, WEBSOCKET_PORT
from .models import TradeEvent, WalletPosition, MarketContext


class WebSocketServer:
    """WebSocket server for broadcasting real-time updates."""

    def __init__(self):
        self.clients: Set[Any] = set()
        self.running = False
        self.message_count = 0

    async def register(self, websocket):
        """Register a new client connection."""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")

        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "connected",
                "data": {
                    "message": "Connected to Bot Trading Tracker",
                    "timestamp": datetime.now().isoformat()
                }
            }))

            # Keep connection alive
            await websocket.wait_closed()
        finally:
            self.clients.discard(websocket)
            print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, message_type: str, data: Any):
        """Broadcast a message to all connected clients."""
        if not self.clients:
            return

        # Serialize data
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        elif hasattr(data, "dict"):
            data = data.dict()

        message = json.dumps({
            "type": message_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "sequence": self.message_count
        }, default=str)

        self.message_count += 1

        # Broadcast to all clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except Exception:
                disconnected.add(client)

        # Clean up disconnected clients
        self.clients -= disconnected

    async def broadcast_trade(self, trade: TradeEvent):
        """Broadcast a new trade event."""
        await self.broadcast("trade", trade)

    async def broadcast_position(self, position: WalletPosition):
        """Broadcast a position update."""
        await self.broadcast("position", position)

    async def broadcast_market(self, market: MarketContext):
        """Broadcast a market context update."""
        await self.broadcast("market", market)

    async def broadcast_pattern(self, pattern_type: str, pattern: Any):
        """Broadcast a pattern detection."""
        await self.broadcast(f"pattern_{pattern_type}", pattern)

    async def broadcast_stats(self, stats: dict):
        """Broadcast tracker statistics."""
        await self.broadcast("stats", stats)

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)

    async def run(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            print("WebSocket server cannot start: websockets library not installed")
            return

        self.running = True
        print(f"WebSocket server starting on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")

        try:
            async with serve(self.register, WEBSOCKET_HOST, WEBSOCKET_PORT):
                print(f"WebSocket server running on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
                while self.running:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"WebSocket server error: {e}")

    def stop(self):
        """Stop the WebSocket server."""
        self.running = False
