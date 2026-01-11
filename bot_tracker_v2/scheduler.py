"""
Task scheduler - coordinates all background tasks.
Single loop that manages discovery, fetching, and cleanup.
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Optional

from .config import (
    DISCOVERY_INTERVAL,
    RESOLUTION_DELAY,
    CLEANUP_INTERVAL,
    BACKUP_INTERVAL,
    REQUEST_TIMEOUT
)
import aiohttp
from .database import Database
from .services.discovery import MarketDiscovery
from .services.fetcher import TradeFetcher
from .services.prices import PriceStream
from .logger import setup_logger

log = setup_logger(__name__)


class Scheduler:
    """
    Central task coordinator.

    Manages:
    - Market discovery (every 5 min)
    - Trade fetching via Goldsky (when markets resolve)
    - Price subscriptions
    - Data cleanup (hourly)
    - Database backups (daily)
    """

    def __init__(
        self,
        db: Database,
        discovery: MarketDiscovery,
        fetcher: TradeFetcher,
        prices: PriceStream
    ):
        self.db = db
        self.discovery = discovery
        self.fetcher = fetcher
        self.prices = prices

        self.running = False
        self.start_time = datetime.utcnow()

        # Track last run times
        self.last_discovery = 0
        self.last_cleanup = 0
        self.last_backup = 0

        # Stats
        self.markets_discovered = 0
        self.markets_fetched = 0
        self.trades_captured = 0

    async def run(self):
        """Main scheduler loop."""
        self.running = True
        self.start_time = datetime.utcnow()

        log.info("Scheduler started")

        # Subscribe to prices for existing active markets
        self._subscribe_to_existing_markets()

        # Initial discovery
        await self._run_discovery()

        while self.running:
            try:
                now = time.time()

                # Discovery (every DISCOVERY_INTERVAL)
                if now - self.last_discovery >= DISCOVERY_INTERVAL:
                    await self._run_discovery()
                    self.last_discovery = now

                # Check markets ready for fetching via Goldsky
                await self._check_markets_to_fetch()

                # Cleanup (every CLEANUP_INTERVAL)
                if now - self.last_cleanup >= CLEANUP_INTERVAL:
                    await self._run_cleanup()
                    self.last_cleanup = now

                # Backup (every BACKUP_INTERVAL)
                if now - self.last_backup >= BACKUP_INTERVAL:
                    self._run_backup()
                    self.last_backup = now

                # Sleep with smart timing based on next market
                sleep_time = self._calculate_sleep_time()
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                log.info("Scheduler cancelled")
                break
            except Exception as e:
                log.error(f"Scheduler error: {e}")
                await asyncio.sleep(10)

        log.info("Scheduler stopped")

    def stop(self):
        """Stop the scheduler."""
        self.running = False

    def _subscribe_to_existing_markets(self):
        """Subscribe to price stream for existing active markets."""
        now = int(time.time())
        active_markets = self.db.get_active_markets()
        subscribed = 0

        for market in active_markets:
            end_time = market.get("end_time")
            if not end_time or end_time <= now:
                continue

            up_token = market.get("up_token_id")
            down_token = market.get("down_token_id")

            if up_token:
                self.prices.subscribe(up_token, market["slug"], "Up")
                subscribed += 1
            if down_token:
                self.prices.subscribe(down_token, market["slug"], "Down")
                subscribed += 1

        if subscribed:
            log.info(f"Subscribed to {subscribed} price streams for existing markets")

    async def _run_discovery(self):
        """Run market discovery."""
        try:
            new_markets = await self.discovery.discover()

            for market in new_markets:
                self.markets_discovered += 1

                # Subscribe to prices for active markets
                if not market.get("resolved") and market.get("end_time"):
                    now = int(time.time())
                    if market["end_time"] > now:
                        # Market is still active
                        up_token = market.get("up_token_id")
                        down_token = market.get("down_token_id")

                        if up_token:
                            self.prices.subscribe(up_token, market["slug"], "Up")
                        if down_token:
                            self.prices.subscribe(down_token, market["slug"], "Down")

            log.info(f"Discovery complete: {len(new_markets)} new, {self.markets_discovered} total")

        except Exception as e:
            log.error(f"Discovery error: {e}")

    async def _check_markets_to_fetch(self):
        """
        Fetch trades for resolved markets using Goldsky subgraph.

        Uses on-chain data for 100% trade capture accuracy.
        """
        now = int(time.time())
        ready_time = now - RESOLUTION_DELAY

        # Get markets that ended and are ready for fetching
        markets = self.db.get_markets_to_fetch()

        for market in markets:
            end_time = market.get("end_time")
            if not end_time or end_time > ready_time:
                continue

            slug = market['slug']

            try:
                # Fetch all trades via Goldsky subgraph
                trades = await self.fetcher.fetch_market_trades(market)
                self.trades_captured += len(trades)
                self.markets_fetched += 1

                log.info(f"Market fetched: {slug} ({len(trades)} trades)")

                # Unsubscribe from prices
                up_token = market.get("up_token_id")
                down_token = market.get("down_token_id")
                if up_token:
                    self.prices.unsubscribe(up_token)
                if down_token:
                    self.prices.unsubscribe(down_token)

            except Exception as e:
                log.error(f"Market fetch error for {slug}: {e}")

    async def _run_cleanup(self):
        """Run periodic cleanup tasks."""
        try:
            # Cleanup old prices (keep 24h)
            deleted = self.db.cleanup_old_prices(hours=24)
            if deleted:
                log.info(f"Cleaned up {deleted} old prices")

            # Log stats
            trade_count = self.db.get_trade_count()
            active_markets = len(self.db.get_active_markets())

            log.info(f"Stats: {trade_count} trades, {active_markets} active markets, {len(self.prices.subscribed_assets)} price subs")

        except Exception as e:
            log.error(f"Cleanup error: {e}")

    def _run_backup(self):
        """Run database backup."""
        try:
            backup_path = self.db.backup()
            if backup_path:
                log.info(f"Backup created: {backup_path}")
        except Exception as e:
            log.error(f"Backup error: {e}")

    def _calculate_sleep_time(self) -> float:
        """
        Calculate optimal sleep time based on upcoming events.

        Smart timing: wake up when next market is ready for fetching.
        """
        now = int(time.time())

        # Get pending markets (not yet fetched)
        markets = self.db.get_markets_to_fetch()

        if not markets:
            # No pending markets, use default discovery interval
            return min(60.0, DISCOVERY_INTERVAL)

        # Find soonest market ready time
        soonest = float('inf')
        for market in markets:
            end_time = market.get("end_time")
            if end_time:
                ready_time = end_time + RESOLUTION_DELAY
                if ready_time > now:
                    soonest = min(soonest, ready_time - now)

        if soonest == float('inf'):
            return 30.0  # Default check interval

        # Add small buffer, cap at reasonable max
        sleep_time = min(soonest + 5, 60.0)
        return max(1.0, sleep_time)

    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        return {
            "running": self.running,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "markets_discovered": self.markets_discovered,
            "markets_fetched": self.markets_fetched,
            "trades_captured": self.trades_captured,
            "active_price_subs": len(self.prices.subscribed_assets)
        }
