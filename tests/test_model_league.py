from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.app.db.models import ModelGwPick, get_session_factory, init_db
from worker.model_league import freeze_model_picks, league_table


def _frame(element: int, name: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "element": element,
                "name": name,
                "team": "Arsenal",
                "position": "FWD",
                "status": "a",
                "expected_minutes": 90,
                "xpts_gw": 6.0,
            }
        ]
    )


def _result(deadline: datetime, frames: dict) -> dict:
    return {
        "season": "2026-27",
        "target_gw": 1,
        "deadline": deadline.isoformat().replace("+00:00", "Z"),
        "live": {"events": [{"id": 1, "is_current": False, "finished": False}]},
        "frames": frames,
    }


def test_provisional_pick_updates_until_deadline():
    init_db()
    session = get_session_factory()()
    try:
        session.query(ModelGwPick).delete()
        session.commit()
        future = datetime.now(timezone.utc) + timedelta(days=2)
        freeze_model_picks(
            session,
            _result(future, {"A": _frame(10, "First"), "B": _frame(20, "Bee"), "C": _frame(30, "Cee"), "D": _frame(40, "Dee")}),
        )
        freeze_model_picks(
            session,
            _result(future, {"A": _frame(11, "Second"), "B": _frame(20, "Bee"), "C": _frame(30, "Cee"), "D": _frame(40, "Dee")}),
        )
        pick = session.query(ModelGwPick).filter_by(model_key="A", event_id=1).one()
        assert pick.name == "Second"
        assert pick.locked is False
    finally:
        session.close()


def test_locked_pick_is_not_rewritten():
    init_db()
    session = get_session_factory()()
    try:
        session.query(ModelGwPick).delete()
        session.commit()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        freeze_model_picks(
            session,
            _result(past, {"A": _frame(10, "Locked"), "B": _frame(20, "Bee"), "C": _frame(30, "Cee"), "D": _frame(40, "Dee")}),
        )
        freeze_model_picks(
            session,
            _result(past, {"A": _frame(99, "Too late"), "B": _frame(20, "Bee"), "C": _frame(30, "Cee"), "D": _frame(40, "Dee")}),
        )
        pick = session.query(ModelGwPick).filter_by(model_key="A", event_id=1).one()
        assert pick.name == "Locked"
        assert pick.fpl_element_id == 10
        assert pick.locked is True
        table = league_table(session)
        assert table["standings"][0]["weeks"][0]["locked"] is True
    finally:
        session.close()
