# FPL Predictor

Leakage-safe Fantasy Premier League expected-points engine.

This is not a flashy dashboard. The first deliverable is a walk-forward backtest of four transparent models on 2025/26, then current-season xPts that refresh every day at 09:00 Europe/London.

## Status

**Verified**

- Project layout, scoring-rule config, FPL adapter, validation
- Historical 2024/25 and 2025/26 import (29,747 player-gameweek rows after de-duplication; 841 players; 38 GWs)
- Leakage tests and API/health tests (`20 passed`)
- Walk-forward 2025/26 backtest of Models A–D — see `docs/BACKTEST_2025-26.md`
- FastAPI health/status/rankings, 09:00 Europe/London worker, Docker Compose files
- Current 2026/27 GW1 predictions with real next-1/3/5 fixture sums — see `docs/PREDICTIONS_2026_27_GW1.md`
- FastAPI HTML dashboard (Plesk / YetiBets-style: no Node required)
- Next.js dashboard (optional; Docker / local `frontend/`)

**TODO / NOT YET VERIFIED**

- Transfer / squad ILP optimiser
- Recalibrating Model D so ranking quality does not inflate MAE — **v0.1.1 formula is in code; 2025/26 walk-forward not re-run yet**
- Production Docker on the Ubuntu VPS

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
python scripts/predict_current.py
cd frontend
npm install
npm run dev
```

Default local database is SQLite (`fpl_local.db`). Plesk production also uses SQLite. Docker Compose uses PostgreSQL.

## Daily refresh

The worker uses APScheduler with `timezone=Europe/London`, cron 09:00, when you run `python -m worker.main`. On Plesk there is no always-on worker: cron at 06:00 runs `scripts/run_daily_refresh.py` and exits. See `docs/PLESK.md`.

## Docs

- `docs/ARCHITECTURE.md`
- `docs/DATA_SOURCES.md`
- `docs/MODELS.md`
- `docs/BACKTESTING.md`
- `docs/DEPLOYMENT.md`
- `docs/OPERATIONS.md`
- `docs/BACKUP_RESTORE.md`
- `docs/BACKTEST_2025-26.md`
- `docs/PLESK.md` — 4 GB VPS: cleanup, 06:00 cron, uvicorn on :8001
