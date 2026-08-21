# Architecture

```
FPL API / vaastav CSVs
        │
        ▼
 data/clients (adapter)  →  raw JSON snapshots (never overwritten)
        │
        ▼
  validation + normalisation
        │
        ▼
 PostgreSQL (production) or SQLite (local/tests)
        │
        ▼
 features/  →  modelling/  →  player_predictions
        │
        ├── backtest/ (walk-forward, leakage-safe)
        └── worker 09:00 Europe/London
                │
                ▼
         FastAPI reads precomputed rows
```

## Process layout on the VPS

| Container | Role | RAM budget |
| --- | --- | --- |
| fpl-postgres | Source of truth | ~2 GB |
| fpl-backend | FastAPI | ~2 GB |
| fpl-worker | Import, features, models, freeze | ~4 GB |
| fpl-nginx | Reverse proxy | ~256 MB |

Redis is not used. Celery is not used. There is no GPU path.

Predictions are precomputed. HTTP handlers only read `player_predictions`.

## Layers

- `data/` owns unofficial JSON field names.
- `features/` owns rolling statistics and fixture ratings.
- `modelling/` owns xPts and explanations.
- `backend/` owns HTTP.
- `worker/` owns schedule and retries.
