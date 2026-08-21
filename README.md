# FPL Predictor

Leakage-safe Fantasy Premier League expected-points engine.

This is not a flashy dashboard. The first deliverable is a walk-forward backtest of four transparent models on 2025/26, then current-season xPts that refresh every day at 09:00 Europe/London.

## Status

**Verified**

- Project layout, scoring-rule config, FPL adapter, validation
- Historical 2024/25 and 2025/26 import (29,747 player-gameweek rows after de-duplication; 841 players; 38 GWs)
- Leakage tests and API/health tests (`17 passed`)
- Walk-forward 2025/26 backtest of Models A–D — see `docs/BACKTEST_2025-26.md`
- FastAPI health/status/rankings, 09:00 Europe/London worker, Docker Compose files

**TODO / NOT YET VERIFIED**

- Current 2026/27 Gameweek 1 published rankings (importer exists; not run end-to-end as a freeze in this session)
- Next.js UI
- Transfer / squad ILP optimiser
- Honest next-3 / next-5 fixture-by-fixture projections (currently scaled placeholders)
- Recalibrating Model D so ranking quality does not inflate MAE

## Quick start (local, no Docker)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
python scripts/download_historical.py
python scripts/inspect_historical.py
pytest
python scripts/run_backtest.py
```

Default local database is SQLite (`fpl_local.db`). Production uses PostgreSQL via Docker Compose.

## Daily refresh

The worker uses APScheduler with `timezone=Europe/London`, cron 09:00. That follows GMT/BST automatically. Failed imports retry at +10 / +30 / +60 minutes and keep the last valid prediction set.

## Docs

- `docs/ARCHITECTURE.md`
- `docs/DATA_SOURCES.md`
- `docs/MODELS.md`
- `docs/BACKTESTING.md`
- `docs/DEPLOYMENT.md`
- `docs/OPERATIONS.md`
- `docs/BACKUP_RESTORE.md`
- `docs/DECISION_LOG.md`
