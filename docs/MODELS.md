# Models

Scoring constants are loaded from `config/scoring_rules.yaml`.

| Key | Name | Uses |
| --- | --- | --- |
| A | Form | Rolling points / minutes, expected minutes heuristic |
| B | Form + Fixture | A plus goals-based attack/defence fixture ratings |
| C | Form + Fixture + xG | B with xG/xA team and player shares |
| D | Full | C plus defensive contribution, bonus, cards, promoted-team priors, shrunk H2H |

All four share `modelling/predict.py`. Complexity is gated by `ModelSpec` flags.

## Expected minutes

Weighted last 3/5/8 Gameweek minutes, clipped per fixture. Double Gameweeks reduce per-fixture minutes. A zero-minute latest Gameweek after regular starts is treated as an injury-return risk.

Live runs additionally scale minutes by `chance_of_playing_next_round` when FPL provides it.

## Fixture model

League average 1.35 goals, home advantage 1.10, Poisson clean-sheet probability `exp(-opp_xg)`. Attack and defence fixture ratings are scaled 0–100.

## Model D calibration (v0.1.1)

Official FPL still pays 4 points for a GKP/DEF clean sheet. Model D was paying that on raw Poisson `P(0)`, which explodes when `opp_xg` is too low (floor 0.15 → ~86% CS). It then stacked defensive contribution and **dropped form**, so entire back lines ranked above attackers.

For D only:

- shrink Poisson CS toward a 0.28 league rate and cap at 0.42
- shrink last-5 defensive-contribution points by 0.75
- blend 40% fixture-adjusted form with 60% components so finishing history is not discarded

Models A–C are unchanged. Walk-forward 2025/26 has **not** been re-run against this formula. See `docs/BACKTEST_2025-26.md`.

## H2H

Previous meetings are blended with `weight = n / (n + 8)`. Model D can be compared with `MODEL_D_NO_H2H`.

## Versioning

`MODEL_VERSION` and `FEATURE_VERSION` in `modelling/predict.py` are written onto every prediction. Frozen Gameweek rows must not be regenerated with later data.

## 2025/26 v0.1 result

These numbers are **v0.1.0** (before Model D CS calibration). Model B currently has the best MAE. Model D currently has the best captain and top-10 actuals but worse MAE. Details: `docs/BACKTEST_2025-26.md`.
