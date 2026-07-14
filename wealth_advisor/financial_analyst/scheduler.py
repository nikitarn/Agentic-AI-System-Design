import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from financial_analyst.analysis import weekly_review
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)

KNOWN_USERS = ["default_user"]  # single-user system for now


def run_weekly_review_all_users() -> None:
    """Sync wrapper — runs the async weekly review pipeline for every known
    user. Safe to call from a scheduler job (sync context) or a CLI flag."""
    for user_id in KNOWN_USERS:
        logger.info(f"Running weekly review for {user_id}")
        try:
            asyncio.run(weekly_review.run(user_id))
        except Exception as e:
            logger.error(f"Weekly review failed for {user_id}: {e}")


def start_scheduler() -> BackgroundScheduler:
    """Start a background cron scheduler (Friday 20:00) for standalone/
    unattended use. NOT started by main.py's interactive REPL — main.py
    already runs its own asyncio event loop, and mixing that with
    BackgroundScheduler's threading model is more complexity than this
    single-user CLI needs. Run this as its own process instead:
    `python -m financial_analyst.scheduler` (stays running, fires weekly), or
    use `financial_analyst --weekly-review` for a one-shot run triggered by
    external cron/launchd — see main.py."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_weekly_review_all_users, CronTrigger(day_of_week="fri", hour=20))
    scheduler.start()
    logger.info("Weekly review scheduler started (Friday 20:00)")
    return scheduler


if __name__ == "__main__":
    import time

    scheduler = start_scheduler()
    try:
        while True:
            time.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
