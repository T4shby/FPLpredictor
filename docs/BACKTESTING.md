# Backtesting

Protocol:

```
history timeline < season_index*100 + N
    → features
    → predict Gameweek N
    → compare with actual points from Gameweek N
    → advance
```

The engine concatenates the prior season after remapping players by FPL `code`, then current-season rows. Double Gameweeks are summed. Blank Gameweeks simply have no fixture rows.

## How to run

```bash
python scripts/download_historical.py
python scripts/run_backtest.py
```

Reports are written to `reports/generated/`.

## Leakage tests

`tests/test_leakage_and_models.py` plants a 20-point spike in GW5 and asserts GW5 features built from GW1–4 cannot see it.
