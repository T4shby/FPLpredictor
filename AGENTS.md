# Agent Guide — FPL Predictor

This repository is a leakage-safe Fantasy Premier League expected-points engine.

## Current phase

Phase 1–3: data foundation, walk-forward backtest, Models A–D.
Do not spend time on visual dashboard polish until the 2025/26 backtest report exists.

## How to work

1. Inspect the repo, tests, and docs before changing behaviour.
2. Implement the smallest complete slice.
3. Run the relevant tests (`pytest`) and, for modelling changes, the walk-forward backtest.
4. Update docs if behaviour or data availability changed.
5. Continue to the next logical task.

Ask the user only for genuine product decisions, unavailable data, security issues, or blockers.

**Live servers:** append every SSH/install/config change to `docs/SERVER_OPS_LOG.md` in the same turn. Never log secret values.

## Key commands

```bash
python scripts/download_historical.py
python scripts/inspect_historical.py
python scripts/run_backtest.py
pytest
uvicorn backend.app.main:app --reload
python -m worker.main
```

## Evidence

A task is not done because files were created. It is done when tests or a generated report demonstrate the behaviour.
