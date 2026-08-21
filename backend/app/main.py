from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.core.logging import configure_logging
from backend.app.core.settings import get_settings
from backend.app.db.models import Gameweek, ModelRun, PlayerPrediction, SystemJob, get_session_factory, init_db

configure_logging(get_settings().log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FPL Predictor", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def db_session():
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def require_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/status")
def status(session: Session = Depends(db_session)):
    settings = get_settings()
    last_job = session.query(SystemJob).order_by(SystemJob.id.desc()).first()
    last_run = session.query(ModelRun).order_by(ModelRun.id.desc()).first()
    next_gw = (
        session.query(Gameweek)
        .filter(Gameweek.season == settings.current_season, Gameweek.is_next.is_(True))
        .one_or_none()
    )
    current_gw = (
        session.query(Gameweek)
        .filter(Gameweek.season == settings.current_season, Gameweek.is_current.is_(True))
        .one_or_none()
    )
    return {
        "season": settings.current_season,
        "model_version": settings.model_version,
        "feature_version": settings.feature_version,
        "timezone": settings.timezone,
        "daily_refresh": f"{settings.daily_refresh_hour:02d}:{settings.daily_refresh_minute:02d} {settings.timezone}",
        "current_gameweek": current_gw.event_id if current_gw else None,
        "next_gameweek": next_gw.event_id if next_gw else None,
        "next_deadline": next_gw.deadline_time.isoformat() if next_gw and next_gw.deadline_time else None,
        "last_job": None
        if last_job is None
        else {
            "name": last_job.job_name,
            "status": last_job.status,
            "finished_at": last_job.finished_at.isoformat() if last_job.finished_at else None,
            "message": last_job.message,
        },
        "last_prediction_run": None
        if last_run is None
        else {
            "model_key": last_run.model_key,
            "status": last_run.status,
            "finished_at": last_run.finished_at.isoformat() if last_run.finished_at else None,
            "frozen": last_run.frozen,
        },
        "data_status": "stale" if last_job is not None and last_job.status == "failed" else "ok",
    }


@app.get("/api/v1/rankings")
def rankings(
    model: str = Query(default="B"),
    position: str | None = None,
    limit: int = 50,
    session: Session = Depends(db_session),
):
    latest = (
        session.query(ModelRun)
        .filter(ModelRun.model_key == model, ModelRun.status == "completed")
        .order_by(ModelRun.id.desc())
        .first()
    )
    if latest is None:
        return {"model": model, "rows": [], "note": "No completed prediction run yet."}
    query = session.query(PlayerPrediction).filter(PlayerPrediction.model_run_id == latest.id)
    rows = query.order_by(PlayerPrediction.xpts_gw.desc()).limit(500).all()
    payload = []
    for row in rows:
        expl = row.explanation or {}
        if position and expl.get("position") != position:
            continue
        if (row.expected_minutes or 0) < 1:
            continue
        payload.append(
            {
                "element": row.fpl_element_id,
                "name": expl.get("name"),
                "team": expl.get("team"),
                "position": expl.get("position"),
                "opponent": expl.get("opponent"),
                "was_home": expl.get("was_home"),
                "price": None if expl.get("now_cost") is None else round(float(expl["now_cost"]) / 10.0, 1),
                "ownership": expl.get("selected_by_percent"),
                "status": expl.get("status"),
                "event_id": row.event_id,
                "xpts_gw": row.xpts_gw,
                "xpts_3gw": row.xpts_3gw,
                "xpts_5gw": row.xpts_5gw,
                "expected_minutes": row.expected_minutes,
                "start_probability": row.start_probability,
                "attack_fixture_rating": row.attack_fixture_rating,
                "defence_fixture_rating": row.defence_fixture_rating,
                "explanation": expl,
            }
        )
        if len(payload) >= limit:
            break
    return {"model": model, "model_run_id": latest.id, "event_id": latest.target_event_id, "rows": payload}


@app.get("/api/v1/picks")
def picks(model: str = Query(default="B"), session: Session = Depends(db_session)):
    import pandas as pd

    from worker.predict_current import category_records

    latest = (
        session.query(ModelRun)
        .filter(ModelRun.model_key == model, ModelRun.status == "completed")
        .order_by(ModelRun.id.desc())
        .first()
    )
    if latest is None:
        return {"model": model, "picks": [], "note": "No completed prediction run yet."}
    rows = session.query(PlayerPrediction).filter(PlayerPrediction.model_run_id == latest.id).all()
    records = []
    for row in rows:
        expl = row.explanation or {}
        records.append(
            {
                "element": row.fpl_element_id,
                "name": expl.get("name"),
                "team": expl.get("team"),
                "position": expl.get("position"),
                "xpts_gw": row.xpts_gw,
                "xpts_3gw": row.xpts_3gw or 0,
                "xpts_5gw": row.xpts_5gw or 0,
                "expected_minutes": row.expected_minutes or 0,
                "selected_by_percent": expl.get("selected_by_percent") or 0,
                "now_cost": expl.get("now_cost") or 0,
                "status": expl.get("status") or "a",
                "value_score": expl.get("value_score")
                or ((row.xpts_3gw or 0) / max((expl.get("now_cost") or 40) / 10.0, 4.0)),
            }
        )
    return {
        "model": model,
        "model_run_id": latest.id,
        "event_id": latest.target_event_id,
        "picks": category_records(pd.DataFrame(records)),
    }


@app.get("/api/v1/players/{element_id}")
def player_detail(element_id: int, model: str = "B", session: Session = Depends(db_session)):
    latest = (
        session.query(ModelRun)
        .filter(ModelRun.model_key == model, ModelRun.status == "completed")
        .order_by(ModelRun.id.desc())
        .first()
    )
    if latest is None:
        raise HTTPException(status_code=404, detail="No prediction run")
    row = (
        session.query(PlayerPrediction)
        .filter(PlayerPrediction.model_run_id == latest.id, PlayerPrediction.fpl_element_id == element_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Player not in latest run")
    return {
        "element": row.fpl_element_id,
        "xpts_gw": row.xpts_gw,
        "xpts_3gw": row.xpts_3gw,
        "xpts_5gw": row.xpts_5gw,
        "expected_minutes": row.expected_minutes,
        "start_probability": row.start_probability,
        "components": row.components,
        "explanation": row.explanation,
        "frozen": row.frozen,
    }


@app.post("/api/v1/admin/refresh")
def admin_refresh(_: None = Depends(require_admin)):
    from worker.jobs import run_daily_refresh

    return run_daily_refresh(triggered_by="admin")
