# Operations

## Schedule

- Daily refresh: 09:00 Europe/London (APScheduler CronTrigger, timezone-aware).
- Deadline freeze: every 15 minutes; if a Gameweek deadline is within 20 minutes, `predictions_frozen` is set.

## Retries

09:00, then +10, +30, +60 minutes. Previous valid predictions are not deleted on failure.

## Admin

`POST /api/v1/admin/refresh` with header `X-Admin-Token`.

## Status

`GET /api/v1/status` exposes last job, last prediction run, next deadline, and data staleness.

## Logs

Structured-ish stdout: `data_import_started`, `data_import_completed`, `job_failed`, `prediction_run_completed`, `gameweek_snapshot_frozen`.
