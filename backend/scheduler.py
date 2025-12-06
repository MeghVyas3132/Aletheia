"""
Background Scheduler for Aletheia

Handles automatic tasks:
- Challenge resolution when voting period ends
- Market resolution
- Periodic cleanup

Uses asyncio for non-blocking background tasks.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional
import traceback

logger = logging.getLogger("Aletheia-Scheduler")


class BackgroundScheduler:
    """
    Background task scheduler using asyncio.
    Runs periodic tasks without blocking the main API.
    """
    
    def __init__(self):
        self.tasks: dict[str, asyncio.Task] = {}
        self.running = False
        self._stop_event: Optional[asyncio.Event] = None
        
    async def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
            
        self.running = True
        self._stop_event = asyncio.Event()
        logger.info("Background scheduler started")
        
    async def stop(self):
        """Stop all scheduled tasks."""
        self.running = False
        if self._stop_event:
            self._stop_event.set()
            
        # Cancel all tasks
        for name, task in self.tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        self.tasks.clear()
        logger.info("Background scheduler stopped")
        
    def schedule_periodic(
        self,
        name: str,
        coro_func: Callable,
        interval_seconds: int,
        run_immediately: bool = False
    ):
        """
        Schedule a coroutine to run periodically.
        
        Args:
            name: Unique task name
            coro_func: Async function to run
            interval_seconds: Seconds between runs
            run_immediately: Whether to run immediately on start
        """
        if name in self.tasks:
            # Cancel existing task
            self.tasks[name].cancel()
            
        async def periodic_wrapper():
            if not run_immediately:
                await asyncio.sleep(interval_seconds)
                
            while self.running:
                try:
                    await coro_func()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in scheduled task '{name}': {e}")
                    logger.error(traceback.format_exc())
                    
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait() if self._stop_event else asyncio.sleep(interval_seconds),
                        timeout=interval_seconds
                    )
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue loop
                    
        task = asyncio.create_task(periodic_wrapper())
        self.tasks[name] = task
        logger.info(f"Scheduled task '{name}' to run every {interval_seconds}s")
        
    def unschedule(self, name: str):
        """Remove a scheduled task."""
        if name in self.tasks:
            self.tasks[name].cancel()
            del self.tasks[name]
            logger.info(f"Unscheduled task '{name}'")


# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


# ==================== Scheduled Tasks ====================

async def resolve_expired_challenges():
    """
    Check and resolve all challenges whose voting period has ended.
    Runs every 5 minutes.
    """
    try:
        # Import here to avoid circular imports
        from dow import get_dow_manager
        
        manager = get_dow_manager()
        resolved = manager.check_and_resolve_challenges()
        
        if resolved:
            logger.info(f"Auto-resolved {len(resolved)} challenge(s)")
            for challenge_id, outcome in resolved:
                logger.info(f"  Challenge {challenge_id}: {outcome}")
                
    except Exception as e:
        logger.error(f"Error resolving challenges: {e}")
        

async def resolve_expired_markets():
    """
    Check and resolve all markets whose resolution time has passed.
    Runs every 10 minutes.
    """
    try:
        # Import here to avoid circular imports
        from market import get_market_manager
        
        manager = get_market_manager()
        
        # Note: Markets require oracle/admin to resolve
        # This just logs pending resolutions
        pending = manager.get_markets_pending_resolution()
        
        if pending:
            logger.info(f"{len(pending)} market(s) pending resolution")
            for market in pending:
                logger.info(f"  Market {market.id}: {market.question[:50]}...")
                
    except Exception as e:
        logger.error(f"Error checking markets: {e}")


async def cleanup_old_data():
    """
    Cleanup old data to prevent memory/storage bloat.
    Runs every hour.
    """
    try:
        # Import here to avoid circular imports
        from dow import get_dow_manager
        from market import get_market_manager
        
        dow_manager = get_dow_manager()
        market_manager = get_market_manager()
        
        # Archive resolved challenges older than 30 days
        cutoff = datetime.now() - timedelta(days=30)
        archived_count = dow_manager.archive_old_challenges(cutoff)
        
        if archived_count > 0:
            logger.info(f"Archived {archived_count} old challenge(s)")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


async def health_check():
    """
    Periodic health check to ensure services are running.
    Runs every minute.
    """
    try:
        # Check database connection
        from dow import get_dow_manager
        manager = get_dow_manager()
        
        # Simple query to verify DB is responsive
        stats = manager.get_treasury_stats()
        
        logger.debug(f"Health check OK - Treasury: {stats.get('balance', 0)} SOL")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")


# ==================== Setup Function ====================

async def setup_scheduler():
    """
    Setup and start the background scheduler with all tasks.
    Call this when the API starts.
    """
    scheduler = get_scheduler()
    await scheduler.start()
    
    # Schedule tasks
    scheduler.schedule_periodic(
        name="resolve_challenges",
        coro_func=resolve_expired_challenges,
        interval_seconds=300,  # Every 5 minutes
        run_immediately=True
    )
    
    scheduler.schedule_periodic(
        name="check_markets",
        coro_func=resolve_expired_markets,
        interval_seconds=600,  # Every 10 minutes
        run_immediately=False
    )
    
    scheduler.schedule_periodic(
        name="cleanup",
        coro_func=cleanup_old_data,
        interval_seconds=3600,  # Every hour
        run_immediately=False
    )
    
    scheduler.schedule_periodic(
        name="health_check",
        coro_func=health_check,
        interval_seconds=60,  # Every minute
        run_immediately=False
    )
    
    logger.info("All background tasks scheduled")
    return scheduler


async def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    scheduler = get_scheduler()
    await scheduler.stop()
