#!/usr/bin/env python
"""One-shot daily refresh for cron (exits when finished)."""

from worker.jobs import run_daily_refresh


def main() -> None:
    result = run_daily_refresh(triggered_by="cron", max_attempts=1)
    print(result)
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
