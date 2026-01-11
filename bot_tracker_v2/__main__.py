"""
Entry point for Bot Tracker v2.
Run with: python -m bot_tracker_v2
"""

import asyncio
import signal
import sys
from datetime import datetime

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    UVICORN_AVAILABLE = False

from .config import HTTP_HOST, HTTP_PORT, TARGET_WALLETS, ensure_dirs
from .database import Database
from .services.discovery import MarketDiscovery
from .services.fetcher import TradeFetcher
from .services.prices import PriceStream
from .services.prefetch import StartupPrefetch
from .scheduler import Scheduler
from . import api
from .logger import setup_logger, log

logger = setup_logger(__name__)


class BotTracker:
    """Main application orchestrator."""

    def __init__(self):
        ensure_dirs()

        self.start_time = datetime.utcnow()
        self.running = False

        # Initialize components
        self.db = Database()
        self.discovery = MarketDiscovery(self.db)
        self.fetcher = TradeFetcher(self.db)
        self.prices = PriceStream(self.db)
        self.prefetch = StartupPrefetch(self.db, self.fetcher)
        self.scheduler = Scheduler(
            self.db,
            self.discovery,
            self.fetcher,
            self.prices
        )

        # Inject dependencies into API
        api.set_dependencies(
            self.db,
            self.prices,
            self.scheduler,
            self.start_time
        )

    async def run(self):
        """Start all services."""
        self.running = True

        # Print startup banner
        self._print_banner()

        # Run startup prefetch (load historical data)
        try:
            await self.prefetch.run(count=10)
        except Exception as e:
            logger.error(f"Prefetch error (continuing anyway): {e}")

        # Create tasks
        tasks = []

        # Scheduler (discovery + fetching)
        scheduler_task = asyncio.create_task(self.scheduler.run())
        tasks.append(scheduler_task)

        # Price stream
        price_task = asyncio.create_task(self.prices.run())
        tasks.append(price_task)

        # HTTP server
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
            logger.error("uvicorn not installed - HTTP server not started")

        # Wait for tasks
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled")

    def stop(self):
        """Stop all services."""
        logger.info("Stopping Bot Tracker...")

        self.running = False
        self.scheduler.stop()
        self.prices.stop()

        # Final backup
        self.db.backup()

        logger.info("Bot Tracker stopped")

    def _print_banner(self):
        """Print startup banner."""
        print()
        print("=" * 60)
        print("BOT TRACKER v2 - Simple & Bulletproof")
        print("=" * 60)
        print()
        print(f"Tracking {len(TARGET_WALLETS)} wallet(s):")
        for addr, name in TARGET_WALLETS.items():
            print(f"  - {name}: {addr[:10]}...{addr[-6:]}")
        print()
        print(f"API: http://{HTTP_HOST}:{HTTP_PORT}")
        print(f"Docs: http://{HTTP_HOST}:{HTTP_PORT}/docs")
        print(f"WebSocket: ws://{HTTP_HOST}:{HTTP_PORT}/ws")
        print()
        print("Startup: Prefetch last 10 markets")
        print("Mode: User-based discovery + Post-resolution trade capture")
        print("=" * 60)
        print()


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

    # Run
    try:
        asyncio.run(tracker.run())
    except KeyboardInterrupt:
        print("\nShutting down...")
        tracker.stop()


if __name__ == "__main__":
    main()
