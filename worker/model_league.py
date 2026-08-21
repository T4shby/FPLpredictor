from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.db.models import ModelGwPick
from data.clients.fpl_client import FplClient
from modelling.predict import ALL_MODELS


def _best_overall(frame):
    available = frame[
        frame["status"].fillna("a").isin(["a", "d"])
        & (frame["expected_minutes"].fillna(0) >= 30)
    ]
    if available.empty:
        return None
    row = available.sort_values("xpts_gw", ascending=False).iloc[0]
    return {
        "element": int(row["element"]),
        "name": str(row.get("name") or ""),
        "team": str(row.get("team") or ""),
        "position": str(row.get("position") or ""),
        "xpts_gw": float(row.get("xpts_gw") or 0),
    }


def _parse_deadline(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        deadline = value
    else:
        deadline = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return deadline


def _should_lock(result: dict) -> bool:
    now = datetime.now(timezone.utc)
    target = int(result["target_gw"])
    live = result.get("live") or {}
    for ev in live.get("events") or []:
        if int(ev.get("id") or 0) != target:
            continue
        if ev.get("is_current") or ev.get("finished"):
            return True
    deadline = _parse_deadline(result.get("deadline"))
    return bool(deadline and now >= deadline)


def freeze_model_picks(session: Session, result: dict) -> list[dict]:
    """Keep each model's GW player current until deadline, then lock. Never rewrite a locked pick."""
    now = datetime.now(timezone.utc)
    lock = _should_lock(result)
    frozen = []
    for spec in ALL_MODELS:
        frame = result["frames"].get(spec.key)
        if frame is None or frame.empty:
            continue
        overall = _best_overall(frame)
        if overall is None:
            continue
        existing = (
            session.query(ModelGwPick)
            .filter_by(season=result["season"], event_id=int(result["target_gw"]), model_key=spec.key)
            .one_or_none()
        )
        if existing is not None and existing.locked:
            frozen.append({"model": spec.key, "status": "locked", "name": existing.name})
            continue
        if existing is None:
            existing = ModelGwPick(
                season=result["season"],
                event_id=int(result["target_gw"]),
                model_key=spec.key,
                fpl_element_id=int(overall["element"]),
                name=str(overall["name"]),
                team=str(overall.get("team") or ""),
                position=str(overall.get("position") or ""),
                xpts_gw=float(overall.get("xpts_gw") or 0),
                locked=lock,
                frozen_at=now,
            )
            session.add(existing)
        else:
            existing.fpl_element_id = int(overall["element"])
            existing.name = str(overall["name"])
            existing.team = str(overall.get("team") or "")
            existing.position = str(overall.get("position") or "")
            existing.xpts_gw = float(overall.get("xpts_gw") or 0)
            existing.locked = lock
            existing.frozen_at = now
        frozen.append(
            {
                "model": spec.key,
                "status": "locked" if lock else "provisional",
                "name": overall["name"],
            }
        )
    session.commit()
    return frozen


def update_actual_points(session: Session, event_id: int | None = None) -> list[dict]:
    """Fill/refresh actual FPL points for picks. Player lock stays; points can rise during the GW."""
    settings = get_settings()
    query = session.query(ModelGwPick).filter(ModelGwPick.season == settings.current_season)
    if event_id is not None:
        query = query.filter(ModelGwPick.event_id == event_id)
    picks = query.all()
    if not picks:
        return []
    client = FplClient()
    bootstrap = client.bootstrap_static()
    events = {int(ev["id"]): ev for ev in bootstrap.get("events") or []}
    live_points = {int(el["id"]): float(el.get("event_points") or 0) for el in bootstrap.get("elements") or []}
    updated = []
    now = datetime.now(timezone.utc)
    live_cache: dict[int, dict[int, float]] = {}
    for pick in picks:
        ev = events.get(pick.event_id) or {}
        points = None
        if ev.get("is_current") or ev.get("is_next"):
            points = live_points.get(pick.fpl_element_id)
        if (ev.get("finished") or ev.get("is_current")) and pick.event_id not in live_cache:
            try:
                payload = client.event_live(pick.event_id)
                live_cache[pick.event_id] = {
                    int(row["id"]): float((row.get("stats") or {}).get("total_points") or 0)
                    for row in payload.get("elements") or []
                }
            except Exception:
                live_cache[pick.event_id] = {}
        if pick.event_id in live_cache and pick.fpl_element_id in live_cache[pick.event_id]:
            points = live_cache[pick.event_id][pick.fpl_element_id]
        if points is None:
            continue
        pick.actual_points = points
        pick.scored_at = now
        updated.append({"model": pick.model_key, "event_id": pick.event_id, "actual": points})
    session.commit()
    return updated


def league_table(session: Session) -> dict:
    settings = get_settings()
    rows = session.query(ModelGwPick).filter(ModelGwPick.season == settings.current_season).all()
    by_model: dict[str, dict] = {}
    for spec in ALL_MODELS:
        by_model[spec.key] = {
            "model": spec.key,
            "name": spec.name,
            "total": 0.0,
            "weeks": [],
        }
    for pick in rows:
        bucket = by_model.setdefault(
            pick.model_key,
            {"model": pick.model_key, "name": pick.model_key, "total": 0.0, "weeks": []},
        )
        actual = pick.actual_points
        if actual is not None:
            bucket["total"] += float(actual)
        bucket["weeks"].append(
            {
                "event_id": pick.event_id,
                "name": pick.name,
                "team": pick.team,
                "position": pick.position,
                "element": pick.fpl_element_id,
                "xpts_gw": pick.xpts_gw,
                "actual_points": actual,
                "locked": pick.locked,
                "frozen_at": pick.frozen_at.isoformat() if pick.frozen_at else None,
            }
        )
    standings = sorted(by_model.values(), key=lambda row: (-row["total"], row["model"]))
    for row in standings:
        row["weeks"] = sorted(row["weeks"], key=lambda week: week["event_id"])
        row["total"] = round(row["total"], 1)
    return {"season": settings.current_season, "standings": standings}
