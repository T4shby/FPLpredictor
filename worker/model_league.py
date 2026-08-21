from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.db.models import ModelSquad
from data.clients.fpl_client import FplClient
from modelling.predict import ALL_MODELS
from optimisation.squad import apply_one_transfer, frame_to_players, score_squad, select_squad, trim_pool


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


def _previous_squad(session: Session, season: str, model_key: str, event_id: int) -> ModelSquad | None:
    return (
        session.query(ModelSquad)
        .filter(
            ModelSquad.season == season,
            ModelSquad.model_key == model_key,
            ModelSquad.event_id < event_id,
            ModelSquad.locked.is_(True),
        )
        .order_by(ModelSquad.event_id.desc())
        .first()
    )


def _build_squad(session: Session, result: dict, model_key: str, frame) -> dict:
    pool = trim_pool(frame_to_players(frame))
    prev = _previous_squad(session, result["season"], model_key, int(result["target_gw"]))
    if prev is not None:
        owned = [
            {
                "element": int(p["element"]),
                "name": p.get("name") or "",
                "team": p.get("team") or "",
                "position": p.get("position") or "",
                "now_cost": int(p.get("now_cost") or 0),
                "xpts_gw": float(p.get("xpts_gw") or 0),
                "expected_minutes": float(p.get("expected_minutes") or 0),
            }
            for p in (prev.players or [])
        ]
        return apply_one_transfer(owned, pool)
    return select_squad(pool)


def _horizon_pack(frame, xpts_col: str) -> dict | None:
    if frame is None or xpts_col not in getattr(frame, "columns", []):
        return None
    try:
        return select_squad(trim_pool(frame_to_players(frame, xpts_col=xpts_col)), max_swaps=250)
    except ValueError:
        return None


def _view_from_pack(pack: dict, extra: dict | None = None) -> dict:
    players = pack.get("players") or []
    cap_el = pack.get("captain_element")
    vice_el = pack.get("vice_element")
    captain = next((p for p in players if p.get("element") == cap_el), {})
    vice = next((p for p in players if p.get("element") == vice_el), {})
    view = {
        "formation": pack.get("formation") or "",
        "captain": captain.get("name"),
        "captain_element": cap_el,
        "vice": vice.get("name"),
        "vice_element": vice_el,
        "cost": round(int(pack.get("cost_tenths") or 0) / 10.0, 1),
        "bank": round(int(pack.get("bank_tenths") or 0) / 10.0, 1),
        "xpts_xi": pack.get("xpts_xi") or 0,
        "n_transfers": pack.get("n_transfers") or 0,
        "starters": [p for p in players if p.get("starter")],
        "bench": [p for p in players if not p.get("starter")],
    }
    if extra:
        view.update(extra)
    return view


def freeze_model_picks(session: Session, result: dict) -> list[dict]:
    """Build/refresh each model's £100m squad until deadline, then lock. Never rewrite a locked squad."""
    now = datetime.now(timezone.utc)
    lock = _should_lock(result)
    frozen = []
    for spec in ALL_MODELS:
        frame = result["frames"].get(spec.key)
        if frame is None or getattr(frame, "empty", True):
            continue
        existing = (
            session.query(ModelSquad)
            .filter_by(season=result["season"], event_id=int(result["target_gw"]), model_key=spec.key)
            .one_or_none()
        )
        if existing is not None and existing.locked:
            if existing.horizon_3 is None:
                existing.horizon_3 = _horizon_pack(frame, "xpts_3gw")
            if existing.horizon_5 is None:
                existing.horizon_5 = _horizon_pack(frame, "xpts_5gw")
            captain = next((p for p in existing.players if p.get("element") == existing.captain_element), {})
            frozen.append({"model": spec.key, "status": "locked", "name": captain.get("name"), "formation": existing.formation})
            continue
        if existing is not None and lock:
            existing.locked = True
            existing.frozen_at = now
            if existing.horizon_3 is None:
                existing.horizon_3 = _horizon_pack(frame, "xpts_3gw")
            if existing.horizon_5 is None:
                existing.horizon_5 = _horizon_pack(frame, "xpts_5gw")
            captain = next((p for p in existing.players if p.get("element") == existing.captain_element), {})
            frozen.append({"model": spec.key, "status": "locked", "name": captain.get("name"), "formation": existing.formation})
            continue
        built = _build_squad(session, result, spec.key, frame)
        payload = dict(
            formation=built["formation"],
            captain_element=int(built["captain_element"]),
            vice_element=int(built["vice_element"]),
            cost_tenths=int(built["cost_tenths"]),
            bank_tenths=int(built["bank_tenths"]),
            xpts_xi=float(built["xpts_xi"]),
            n_transfers=int(built["n_transfers"]),
            players=built["players"],
            horizon_3=_horizon_pack(frame, "xpts_3gw"),
            horizon_5=_horizon_pack(frame, "xpts_5gw"),
            locked=lock,
            frozen_at=now,
        )
        if existing is None:
            session.add(
                ModelSquad(
                    season=result["season"],
                    event_id=int(result["target_gw"]),
                    model_key=spec.key,
                    **payload,
                )
            )
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
        captain = next((p for p in built["players"] if p["element"] == built["captain_element"]), {})
        frozen.append(
            {
                "model": spec.key,
                "status": "locked" if lock else "provisional",
                "name": captain.get("name"),
                "formation": built["formation"],
                "cost": built["cost_tenths"] / 10.0,
            }
        )
    session.commit()
    return frozen


def update_actual_points(session: Session, event_id: int | None = None) -> list[dict]:
    settings = get_settings()
    query = session.query(ModelSquad).filter(ModelSquad.season == settings.current_season)
    if event_id is not None:
        query = query.filter(ModelSquad.event_id == event_id)
    rows = query.all()
    if not rows:
        return []
    client = FplClient()
    bootstrap = client.bootstrap_static()
    events = {int(ev["id"]): ev for ev in bootstrap.get("events") or []}
    live_points = {int(el["id"]): float(el.get("event_points") or 0) for el in bootstrap.get("elements") or []}
    updated = []
    now = datetime.now(timezone.utc)
    live_cache: dict[int, dict[int, dict]] = {}
    for row in rows:
        ev = events.get(row.event_id) or {}
        if row.event_id not in live_cache:
            stats: dict[int, dict] = {
                eid: {"points": pts, "minutes": 0} for eid, pts in live_points.items()
            }
            if ev.get("finished") or ev.get("is_current"):
                try:
                    payload = client.event_live(row.event_id)
                    for item in payload.get("elements") or []:
                        eid = int(item["id"])
                        st = item.get("stats") or {}
                        stats[eid] = {
                            "points": float(st.get("total_points") or live_points.get(eid) or 0),
                            "minutes": int(st.get("minutes") or 0),
                        }
                except Exception:
                    pass
            live_cache[row.event_id] = stats
        scored = score_squad(
            row.players or [],
            row.captain_element,
            row.vice_element,
            live_cache[row.event_id],
            bool(ev.get("finished")),
        )
        row.actual_points = scored["actual_points"]
        row.scored_at = now
        updated.append({"model": row.model_key, "event_id": row.event_id, "actual": scored["actual_points"]})
    session.commit()
    return updated


def league_table(session: Session) -> dict:
    settings = get_settings()
    rows = session.query(ModelSquad).filter(ModelSquad.season == settings.current_season).all()
    by_model: dict[str, dict] = {}
    for spec in ALL_MODELS:
        by_model[spec.key] = {"model": spec.key, "name": spec.name, "total": 0.0, "weeks": []}
    for row in rows:
        bucket = by_model.setdefault(row.model_key, {"model": row.model_key, "name": row.model_key, "total": 0.0, "weeks": []})
        actual = row.actual_points
        if actual is not None:
            bucket["total"] += float(actual)
        players = row.players or []
        pack = {
            "players": players,
            "formation": row.formation,
            "captain_element": row.captain_element,
            "vice_element": row.vice_element,
            "cost_tenths": row.cost_tenths,
            "bank_tenths": row.bank_tenths,
            "xpts_xi": row.xpts_xi,
            "n_transfers": row.n_transfers,
        }
        week = _view_from_pack(
            pack,
            extra={
                "event_id": row.event_id,
                "actual_points": actual,
                "locked": row.locked,
                "frozen_at": row.frozen_at.isoformat() if row.frozen_at else None,
                "horizon_3": _view_from_pack(row.horizon_3) if row.horizon_3 else None,
                "horizon_5": _view_from_pack(row.horizon_5) if row.horizon_5 else None,
            },
        )
        bucket["weeks"].append(week)
    standings = sorted(by_model.values(), key=lambda row: (-row["total"], row["model"]))
    for row in standings:
        row["weeks"] = sorted(row["weeks"], key=lambda week: week["event_id"])
        row["total"] = round(row["total"], 1)
        latest = row["weeks"][-1] if row["weeks"] else None
        row["latest"] = latest
    return {"season": settings.current_season, "standings": standings}
