"""
Main entry point for the bot trading tracker.
Orchestrates all components and runs the server.
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import List

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    UVICORN_AVAILABLE = False
    print("Warning: uvicorn not installed. Run: pip install uvicorn")

from .config import HTTP_HOST, HTTP_PORT, TARGET_WALLETS
from .models import TradeEvent
from .trade_poller import TradePoller
from .market_context import MarketContextFetcher
from .position_tracker import PositionTracker
from .pattern_detector import PatternDetector
from .storage import JSONStorage
from .price_stream import PriceStream, PriceUpdate
from . import api


class BotTracker:
    """Main orchestrator for the bot trading tracker."""

    def __init__(self):
        self.start_time = datetime.now()

        # Initialize components
        self.position_tracker = PositionTracker()
        self.pattern_detector = PatternDetector()
        self.market_fetcher = MarketContextFetcher()
        self.trade_poller = TradePoller(self.on_new_trades)
        self.storage = JSONStorage()  # JSON file storage
        self.price_stream = PriceStream(
            on_price_update=self.on_price_update
        )

        # Inject dependencies into API
        api.set_dependencies(
            self.position_tracker,
            self.pattern_detector,
            self.market_fetcher,
            None,  # WebSocket now handled by FastAPI
            self.start_time
        )
        api.set_trade_poller(self.trade_poller)

        self.running = False
        self.price_update_count = 0

    async def on_price_update(self, update: PriceUpdate):
        """Handle price update from WebSocket - save to storage."""
        self.storage.save_price_update(
            market_slug=update.market_slug,
            outcome=update.outcome,
            price=update.price,
            best_bid=update.best_bid,
            best_ask=update.best_ask,
            timestamp=update.timestamp
        )
        self.price_update_count += 1

        # Log periodically
        if self.price_update_count % 100 == 0:
            print(f"Price updates saved: {self.price_update_count}")

    async def on_new_trades(self, trades: List[TradeEvent]):
        """Handle new trades from the poller."""
        for trade in trades:
            # Save trade to JSON file
            self.storage.save_trade(trade)

            # Ensure we have market context
            if trade.market_slug and trade.market_slug not in self.market_fetcher.cache:
                context = await self.market_fetcher.get_or_fetch_context(slug=trade.market_slug)
                if context:
                    self.storage.save_market(context)  # Save market metadata
                    await api.broadcast_to_websocket("market", context.model_dump())

                    # Subscribe to price stream for this market
                    up_token = context.token_ids.get("up", "")
                    down_token = context.token_ids.get("down", "")
                    if up_token:
                        self.price_stream.add_asset(up_token, context.slug, "Up")
                    if down_token:
                        self.price_stream.add_asset(down_token, context.slug, "Down")
                    print(f"Subscribed to price stream: {context.slug}")

            # Update position
            position = self.position_tracker.update_position(trade)

            # Save position snapshot
            self.storage.save_position(position)

            # Record for pattern detection
            self.pattern_detector.record_trade(trade)

            # Add to API trade history
            api.add_trade_to_history(trade)

            # Broadcast via WebSocket (using FastAPI WebSocket)
            await api.broadcast_to_websocket("trade", trade.model_dump())
            await api.broadcast_to_websocket("position", position.model_dump())

            # Analyze and broadcast patterns
            market = self.market_fetcher.cache.get(trade.market_slug)
            timing = self.pattern_detector.analyze_timing(trade.wallet, trade.market_slug, market)
            price = self.pattern_detector.analyze_price(trade.wallet, trade.market_slug)
            hedge = self.pattern_detector.analyze_hedge(position)

            if timing:
                await api.broadcast_to_websocket("timing", timing.model_dump())
            if price:
                await api.broadcast_to_websocket("price", price.model_dump())
            if hedge:
                await api.broadcast_to_websocket("hedge", hedge.model_dump())

        # Broadcast updated stats
        stats = self.position_tracker.get_summary()
        stats["connected_clients"] = api.ws_manager.get_count()
        await api.broadcast_to_websocket("stats", stats)

    async def run(self):
        """Start all services."""
        self.running = True

        print("=" * 60)
        print("BOT TRADING TRACKER")
        print("=" * 60)
        print(f"Tracking {len(TARGET_WALLETS)} wallets:")
        for addr, name in TARGET_WALLETS.items():
            print(f"  - {name}: {addr[:10]}...{addr[-6:]}")
        print()
        print(f"Data saved to: {self.storage.db_dir}")
        print()
        print(f"HTTP API: http://{HTTP_HOST}:{HTTP_PORT}")
        print(f"API Docs: http://{HTTP_HOST}:{HTTP_PORT}/docs")
        print(f"WebSocket: ws://{HTTP_HOST}:{HTTP_PORT}/ws")
        print(f"Price Stream: Real-time prices via Polymarket WebSocket")
        print("=" * 60)
        print()

        # Create tasks for all services
        tasks = []

        # Trade poller
        poller_task = asyncio.create_task(self.trade_poller.run())
        tasks.append(poller_task)

        # Market context refresher
        market_task = asyncio.create_task(self.market_fetcher.run())
        tasks.append(market_task)

        # Price stream (real-time prices from Polymarket)
        price_task = asyncio.create_task(self.price_stream.run())
        tasks.append(price_task)

        # HTTP server (uvicorn)
        if UVICORN_AVAILABLE:
            config = uvicorn.Config(
                api.app,
                host=HTTP_HOST,
                port=HTTP_PORT,
                log_level="info"
            )
            server = uvicorn.Server(config)
            http_task = asyncio.create_task(server.serve())
            tasks.append(http_task)
        else:
            print("HTTP server not started: uvicorn not installed")

        # Wait for all tasks
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("Shutting down...")

    def stop(self):
        """Stop all services."""
        self.running = False
        self.trade_poller.stop()
        self.market_fetcher.stop()
        self.price_stream.stop()

        # Save final data
        self.storage.flush()
        summary = self.storage.get_session_summary()
        print(f"\nSession saved: {summary['session_trades_count']} trades, {summary['total_positions_count']} positions")
        print(f"Data location: {summary['db_dir']}")


def main():
    """Entry point."""
    tracker = BotTracker()

    # Handle shutdown signals
    def signal_handler(sig, frame):
        print("\nReceived shutdown signal...")
        tracker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the tracker
    try:
        asyncio.run(tracker.run())
    except KeyboardInterrupt:
        print("\nShutting down...")
        tracker.stop()


if __name__ == "__main__":
    main()
