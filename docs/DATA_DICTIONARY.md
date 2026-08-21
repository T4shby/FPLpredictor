# Data dictionary — 2025-26

Rows: **29747**
Players: **841**
Gameweeks: **1–38** (38 unique)
Validation: **OK**

## Columns in merged_gw

| Column | Non-null | Nulls |
| --- | ---: | ---: |
| `name` | 29747 | 0 |
| `position` | 29747 | 0 |
| `team` | 29747 | 0 |
| `xP` | 29747 | 0 |
| `assists` | 29747 | 0 |
| `bonus` | 29747 | 0 |
| `bps` | 29747 | 0 |
| `clean_sheets` | 29747 | 0 |
| `creativity` | 29747 | 0 |
| `element` | 29747 | 0 |
| `expected_assists` | 29747 | 0 |
| `expected_goal_involvements` | 29747 | 0 |
| `expected_goals` | 29747 | 0 |
| `expected_goals_conceded` | 29747 | 0 |
| `fixture` | 29747 | 0 |
| `goals_conceded` | 29747 | 0 |
| `goals_scored` | 29747 | 0 |
| `ict_index` | 29747 | 0 |
| `influence` | 29747 | 0 |
| `kickoff_time` | 29747 | 0 |
| `minutes` | 29747 | 0 |
| `modified` | 29747 | 0 |
| `opponent_team` | 29747 | 0 |
| `own_goals` | 29747 | 0 |
| `penalties_missed` | 29747 | 0 |
| `penalties_saved` | 29747 | 0 |
| `red_cards` | 29747 | 0 |
| `round` | 29747 | 0 |
| `saves` | 29747 | 0 |
| `selected` | 29747 | 0 |
| `starts` | 29747 | 0 |
| `team_a_score` | 29747 | 0 |
| `team_h_score` | 29747 | 0 |
| `threat` | 29747 | 0 |
| `total_points` | 29747 | 0 |
| `transfers_balance` | 29747 | 0 |
| `transfers_in` | 29747 | 0 |
| `transfers_out` | 29747 | 0 |
| `value` | 29747 | 0 |
| `was_home` | 29747 | 0 |
| `yellow_cards` | 29747 | 0 |
| `clearances_blocks_interceptions` | 29747 | 0 |
| `defensive_contribution` | 29747 | 0 |
| `recoveries` | 29747 | 0 |
| `tackles` | 29747 | 0 |
| `GW` | 29747 | 0 |
| `season` | 29747 | 0 |

## Feature classification

| Field | Class | Source | Notes |
| --- | --- | --- | --- |
| `minutes` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | Playing time |
| `starts` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | Start flag |
| `total_points` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | Actual FPL points |
| `goals_scored` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | Goals |
| `assists` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | Assists |
| `expected_goals` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | Player xG |
| `expected_assists` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | Player xA |
| `expected_goals_conceded` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | Player xGC |
| `defensive_contribution` | DIRECTLY AVAILABLE | vaastav merged_gw / FPL live | DEFCON FPL points |
| `clearances_blocks_interceptions` | DIRECTLY AVAILABLE | vaastav / FPL live | CBIT count |
| `recoveries` | DIRECTLY AVAILABLE | vaastav / FPL live | Ball recoveries |
| `tackles` | DIRECTLY AVAILABLE | vaastav / FPL live | Tackles |
| `bonus` | DIRECTLY AVAILABLE | vaastav / FPL live | Bonus points |
| `bps` | DIRECTLY AVAILABLE | vaastav / FPL live | Bonus point system score |
| `saves` | DIRECTLY AVAILABLE | vaastav / FPL live | GK saves |
| `value` | DIRECTLY AVAILABLE | vaastav merged_gw | Price in tenths of a million at that GW |
| `selected` | DIRECTLY AVAILABLE | vaastav merged_gw | Ownership count/percent depending on file |
| `chance_of_playing_next_round` | DIRECTLY AVAILABLE | FPL live bootstrap only | Not in historical merged_gw |
| `penalties_order` | DIRECTLY AVAILABLE | FPL live bootstrap | Historical penalty taker flag is incomplete |
| `pp90_l3` | DERIVED | rolling features | Points per 90 over last 3 GWs |
| `attack_rating` | DERIVED | team strength | Goals-based attack rating |
| `xg_attack_rating` | DERIVED | team strength | xG-based attack rating |
| `attack_fixture_rating` | DERIVED | fixture model | 0-100 attacking fixture rating |
| `defence_fixture_rating` | DERIVED | fixture model | 0-100 defensive fixture rating |
| `expected_minutes` | DERIVED | minutes heuristic | Explainable minutes model |
| `team_xg` | DERIVED | Poisson/attack-defence | Expected team goals in this fixture |
| `p_clean_sheet` | DERIVED | Poisson P(0) | Clean sheet probability |
| `h2h_goals_for` | DERIVED | previous meetings | Shrunk H2H feature |
| `championship_xg` | NOT CURRENTLY AVAILABLE | external | Promoted-team Championship xG not ingested |
| `european_fixtures` | NOT CURRENTLY AVAILABLE | external | UEFA rest/congestion not ingested |
| `set_piece_taker_history` | EXTERNAL SOURCE REQUIRED | FPL live has order fields; historical incomplete | Use live penalties_order |
