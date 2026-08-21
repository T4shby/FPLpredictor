from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.app.core.logging import configure_logging
from backend.app.core.settings import get_settings
from worker.jobs import run_daily_refresh, run_deadline_freeze

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    tz = ZoneInfo(settings.timezone)
    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(
        run_daily_refresh,
        CronTrigger(hour=settings.daily_refresh_hour, minute=settings.daily_refresh_minute, timezone=tz),
        id="daily_refresh",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_deadline_freeze,
        CronTrigger(minute="*/15", timezone=tz),
        id="deadline_freeze",
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "worker_started timezone=%s daily=%02d:%02d",
        settings.timezone,
        settings.daily_refresh_hour,
        settings.daily_refresh_minute,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("worker_stopped")


if __name__ == "__main__":
    main()
