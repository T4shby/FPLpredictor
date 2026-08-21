from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.app.core.settings import get_settings
from backend.app.db.models import Gameweek, get_session_factory, init_db
from data.ingestion.live import import_live_snapshot, record_job
from worker.model_league import update_actual_points
from worker.predict_current import generate_current_predictions

logger = logging.getLogger(__name__)

RETRY_DELAYS_MINUTES = (0, 10, 30, 60)


def run_daily_refresh(triggered_by: str = "schedule", max_attempts: int | None = None) -> dict:
    settings = get_settings()
    init_db()
    factory = get_session_factory()
    last_error = None
    delays = RETRY_DELAYS_MINUTES
    if triggered_by == "cron" or max_attempts == 1:
        delays = (0,)
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            logger.info("refresh_retry_wait minutes=%s attempt=%s", delay, attempt)
            time.sleep(delay * 60)
        session = factory()
        try:
            logger.info("data_import_started attempt=%s triggered_by=%s", attempt, triggered_by)
            result = import_live_snapshot(session)
            if not result.get("ok"):
                raise RuntimeError(str(result.get("errors")))
            logger.info("data_import_completed players=%s", result.get("players"))
            pred = generate_current_predictions(session)
            scored = update_actual_points(session)
            record_job(session, "daily_refresh", "success", message=f"attempt {attempt}", attempt=attempt, details=result)
            logger.info("prediction_run_completed models=%s league=%s", pred.get("models"), scored)
            return {"ok": True, "import": result, "predictions": pred, "league": scored, "attempt": attempt}
        except Exception as exc:
            last_error = exc
            logger.exception("job_failed attempt=%s error=%s", attempt, exc)
            record_job(session, "daily_refresh", "failed", message=str(exc), attempt=attempt)
        finally:
            session.close()
    return {"ok": False, "error": str(last_error)}


def run_deadline_freeze() -> dict:
    """Freeze the latest prediction run if a Gameweek deadline is inside the next 20 minutes."""
    settings = get_settings()
    init_db()
    session = get_session_factory()()
    try:
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(minutes=20)
        gameweeks = (
            session.query(Gameweek)
            .filter(Gameweek.season == settings.current_season, Gameweek.predictions_frozen.is_(False))
            .all()
        )
        frozen = []
        for gw in gameweeks:
            if gw.deadline_time is None:
                continue
            deadline = gw.deadline_time
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if now <= deadline <= horizon:
                gw.predictions_frozen = True
                frozen.append(gw.event_id)
                logger.info("gameweek_snapshot_frozen event_id=%s deadline=%s", gw.event_id, deadline.isoformat())
        session.commit()
        return {"ok": True, "frozen": frozen}
    finally:
        session.close()
