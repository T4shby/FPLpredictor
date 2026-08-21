#!/usr/bin/env python
"""Import live FPL data and generate current-season predictions."""

from backend.app.db.models import get_session_factory, init_db
from worker.jobs import run_daily_refresh


def main() -> None:
    init_db()
    result = run_daily_refresh(triggered_by="cli")
    print(result)


if __name__ == "__main__":
    main()
