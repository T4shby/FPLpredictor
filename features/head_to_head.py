from __future__ import annotations

import pandas as pd

from features.team_strength import unique_team_matches


def head_to_head_goals(
    history: pd.DataFrame,
    team: str,
    opponent: str,
    max_meetings: int = 6,
) -> dict[str, float]:
    matches = unique_team_matches(history)
    mask = (matches["team"] == team) & (matches["opponent_team"].astype(str) == str(opponent))
    subset = matches.loc[mask].sort_values(["season", "GW"]).tail(max_meetings)
    if subset.empty:
        return {"n_meetings": 0, "h2h_goals_for": None, "h2h_goals_against": None}
    return {
        "n_meetings": int(len(subset)),
        "h2h_goals_for": float(subset["team_goals_for"].mean()),
        "h2h_goals_against": float(subset["team_goals_against"].mean()),
    }


def blend_h2h(model_xg: float, h2h_goals: float | None, n_meetings: int, prior_strength: int = 8) -> float:
    if not n_meetings or h2h_goals is None:
        return model_xg
    w = n_meetings / (n_meetings + prior_strength)
    return (1 - w) * model_xg + w * h2h_goals
