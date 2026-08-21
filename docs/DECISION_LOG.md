# Decision log

| Date | Decision | Why |
| --- | --- | --- |
| 2026-08-21 | PostgreSQL in production, SQLite for local/tests | Spec requires Postgres; Docker is not installed on the current Windows dev machine |
| 2026-08-21 | APScheduler in the worker, not Celery | Single VPS, one worker, timezone-aware cron is enough |
| 2026-08-21 | No Redis | No queue or shared lock requirement yet |
| 2026-08-21 | Adapter layer around unofficial FPL JSON | Upstream fields must not leak into models |
| 2026-08-21 | Cross-season player identity via FPL `code` | Element IDs reset every season |
| 2026-08-21 | Scoring rules in YAML copied from live `game_config.scoring` | Avoid hard-coded point values |
| 2026-08-21 | Transparent statistical Models A–D before ML | Complexity must win a walk-forward backtest first |
| 2026-08-21 | No Next.js UI in phase 1 | Spec: backtest before dashboard polish |
| 2026-08-21 | Publish Model B for xPts and captain | B won 2025/26 MAE; D ranks well but over-weights clean sheets |
| 2026-08-21 | Treat null FPL `chance_of_playing_next_round` as 100% if status is available | NaN was zeroing most of the squad |
| 2026-08-21 | Do not treat previous-season final-GW rest as injury | Season-start minutes were being halved for regulars |
