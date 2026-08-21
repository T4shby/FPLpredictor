from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.app.db.models import ModelSquad, get_session_factory, init_db
from worker.model_league import freeze_model_picks, league_table


def _pool_frame(shift: int = 0) -> pd.DataFrame:
    rows = []
    eid = 1 + shift * 100
    clubs = [f"T{i}" for i in range(8)]
    for pos, n, base in (("GKP", 6, 40), ("DEF", 12, 45), ("MID", 12, 50), ("FWD", 8, 70)):
        for i in range(n):
            rows.append(
                {
                    "element": eid,
                    "name": f"{pos}{i}-{shift}",
                    "team": clubs[i % 8],
                    "position": pos,
                    "status": "a",
                    "expected_minutes": 90,
                    "now_cost": base + (i % 4) * 5,
                    "xpts_gw": 6.0 - i * 0.12 + shift,
                }
            )
            eid += 1
    return pd.DataFrame(rows)


def _result(deadline: datetime, shift: int = 0) -> dict:
    frame = _pool_frame(shift)
    return {
        "season": "2026-27",
        "target_gw": 1,
        "deadline": deadline.isoformat().replace("+00:00", "Z"),
        "live": {"events": [{"id": 1, "is_current": False, "finished": False}]},
        "frames": {"A": frame, "B": frame, "C": frame, "D": frame},
    }


def test_provisional_squad_updates_until_deadline():
    init_db()
    session = get_session_factory()()
    try:
        session.query(ModelSquad).delete()
        session.commit()
        future = datetime.now(timezone.utc) + timedelta(days=2)
        freeze_model_picks(session, _result(future, shift=0))
        first = session.query(ModelSquad).filter_by(model_key="A", event_id=1).one()
        first_captain = first.captain_element
        first_names = [p["name"] for p in first.players]
        freeze_model_picks(session, _result(future, shift=1))
        second = session.query(ModelSquad).filter_by(model_key="A", event_id=1).one()
        assert first.locked is False
        assert second.locked is False
        assert second.captain_element != first_captain or [p["name"] for p in second.players] != first_names
        assert len(second.players) == 15
        assert len([p for p in second.players if p["starter"]]) == 11
    finally:
        session.close()


def test_locked_squad_is_not_rewritten():
    init_db()
    session = get_session_factory()()
    try:
        session.query(ModelSquad).delete()
        session.commit()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        freeze_model_picks(session, _result(past, shift=0))
        locked = session.query(ModelSquad).filter_by(model_key="A", event_id=1).one()
        captain = locked.captain_element
        freeze_model_picks(session, _result(past, shift=1))
        again = session.query(ModelSquad).filter_by(model_key="A", event_id=1).one()
        assert again.locked is True
        assert again.captain_element == captain
        table = league_table(session)
        assert table["standings"][0]["latest"]["locked"] is True
        assert len(table["standings"][0]["latest"]["starters"]) == 11
    finally:
        session.close()


def test_deadline_locks_existing_squad_without_rebuild():
    init_db()
    session = get_session_factory()()
    try:
        session.query(ModelSquad).delete()
        session.commit()
        future = datetime.now(timezone.utc) + timedelta(days=2)
        freeze_model_picks(session, _result(future, shift=0))
        captain = session.query(ModelSquad).filter_by(model_key="A", event_id=1).one().captain_element
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        freeze_model_picks(session, _result(past, shift=1))
        row = session.query(ModelSquad).filter_by(model_key="A", event_id=1).one()
        assert row.locked is True
        assert row.captain_element == captain
    finally:
        session.close()
