# 2025/26 walk-forward backtest

Generated: 2026-08-21  
Model version: 0.1.0  
Feature version: 0.1.0  
n = 11,361 player-gameweeks with at least 1 minute.

This is a walk-forward check on the **completed 2025/26 season**. It is not a backtest of 2026/27. Live 2026/27 judgement is the model league: each of A–D locks a player at the Gameweek deadline and accrues that player's actual FPL points.

**NOT YET RE-RUN:** Model D CS calibration in v0.1.1 (shrink Poisson CS, DC shrink, 40% form blend) is not reflected in the table below. Those rows are v0.1.0.

Protocol: for Gameweek N, features use only rows with `timeline < N`. Players are aligned across 2024/25 → 2025/26 using FPL `code`, not season-specific element IDs. Top-10 and captain scores are **per Gameweek, then averaged**.

| Model | MAE | RMSE | Corr | Spearman | Top 10 avg actual | Captain avg actual |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Model A - Form | 2.194 | 3.171 | 0.205 | 0.272 | 4.247 | 4.395 |
| Model B - Form + Fixture | **2.082** | **3.112** | **0.236** | **0.302** | 4.458 | 5.132 |
| Model C - Form + Fixture + xG | 2.091 | 3.123 | 0.228 | 0.293 | 4.492 | 5.026 |
| Model D - Full Model | 2.485 | 3.302 | 0.232 | 0.295 | **4.568** | **5.342** |

## What added value

- **Fixture ratings (A → B)** improved every metric. Current team/opponent strength is useful.
- **xG (B → C)** did not beat Model B on MAE, RMSE, correlation, or captain. Top-10 was a small gain. Do not assume xG automatically helps a form+fixture baseline.
- **Full Model D** is the best ranker (captain and top-10) but the worst point predictor (MAE). Component stacking is currently miscalibrated. Use D for ordering, B for expected-point magnitude, until D is recalibrated.

## Not claimed

These are v0.1 transparent statistical models. They are not production-optimal. Injury news is live-only and was not in the historical files, which understates a live Model D.
