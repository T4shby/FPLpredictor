#!/usr/bin/env python
"""Generate current-season predictions and write a report."""

from backend.app.db.models import get_session_factory, init_db
from worker.predict_current import compute_current_predictions, persist_predictions, write_prediction_report


def main() -> None:
    init_db()
    result = compute_current_predictions()
    session = get_session_factory()()
    try:
        published = persist_predictions(session, result)
    finally:
        session.close()
    report = write_prediction_report(result)
    print({"target_gw": result["target_gw"], "deadline": result["deadline"], "models": published, "report": str(report)})
    for key, frame in result["frames"].items():
        top = frame.iloc[0]
        print(key, "top", top["name"], round(float(top["xpts_gw"]), 2))


if __name__ == "__main__":
    main()
