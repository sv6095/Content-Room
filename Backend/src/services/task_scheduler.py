"""
Task Scheduler Service — Content Room

Lightweight background scheduler for maintenance tasks only.
There is NO social media publishing — this app is a content planner, not a publisher.
"""
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class TaskSchedulerService:
    """
    Minimal background scheduler for maintenance tasks.
    Does NOT publish to any social platform.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        """Start the scheduler."""
        if self.is_running:
            return

        # Weekly cleanup of old temporary uploads
        self.scheduler.add_job(
            self._cleanup_old_uploads,
            CronTrigger(day_of_week="sun", hour=4, minute=0),
            id="cleanup_old_uploads",
            name="Cleanup temporary uploads",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("Task scheduler started (maintenance-only mode)")

    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("Task scheduler stopped")

    async def _cleanup_old_uploads(self):
        """Clean up old temporary uploads."""
        logger.info("Running cleanup of old temporary uploads…")
        # TODO: implement storage cleanup if needed

    def get_status(self) -> dict:
        """Get scheduler status."""
        jobs = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                })
        return {"running": self.is_running, "jobs": jobs}


# ─── Singleton ────────────────────────────────────────────

_scheduler_service: Optional[TaskSchedulerService] = None


def get_scheduler_service() -> TaskSchedulerService:
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = TaskSchedulerService()
    return _scheduler_service


def start_scheduler():
    service = get_scheduler_service()
    service.start()
    return service


def stop_scheduler():
    global _scheduler_service
    if _scheduler_service:
        _scheduler_service.stop()
