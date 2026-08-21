# Data sources

| Source | URL / path | Update | Reliability | Licence / notes | Fallback |
| --- | --- | --- | --- | --- | --- |
| FPL bootstrap-static | `https://fantasy.premierleague.com/api/bootstrap-static/` | Daily 09:00 UK | High, unofficial | Public undocumented JSON | Keep last valid snapshot |
| FPL fixtures | `https://fantasy.premierleague.com/api/fixtures/` | Daily 09:00 UK | High, unofficial | Same | Keep last valid snapshot |
| FPL event live | `/event/{id}/live/` | After matches | High, unofficial | Same | Not required for pre-deadline preds |
| vaastav historical | `github.com/vaastav/Fantasy-Premier-League` | Manual download into `data/cache` | High for 2025/26 | Third-party archive | Our own snapshots from 2026/27 onward |
| Scoring rules | `config/scoring_rules.yaml` plus live `game_config.scoring` | Season start | Verified 2026-08-21 | Copied from FPL game_config | YAML file |

Raw responses are stored under `data/snapshots/` with a SHA-256 hash. Historical snapshots are append-only.

FPL element IDs and team IDs are **not** stable across seasons. Cross-season joins use the FPL `code` field from `players_raw.csv` / live bootstrap.

## Verified 2026/27 live fields

Player objects include minutes, starts, goals, assists, xG, xA, xGI, xGC, defensive_contribution, CBIT, recoveries, tackles, chance of playing, penalty/corner/free-kick order, price, ownership.

Team strength fields were `null` on 2026-08-21 (GW1). Do not depend on official FPL FDR/strength early in the season.

## Not currently available

- Championship xG for promoted teams
- European fixture calendar / rest days
- Pre-deadline injury snapshots inside vaastav historical files (`chance_of_playing_*` is live-only)
