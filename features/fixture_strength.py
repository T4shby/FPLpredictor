from __future__ import annotations

import numpy as np
import pandas as pd

from features.team_strength import LEAGUE_GOALS_PRIOR

HOME_ADVANTAGE = 1.10


def poisson_zero(expected_goals) -> np.ndarray:
    lam = np.clip(np.asarray(expected_goals, dtype=float), 0.0, 8.0)
    return np.exp(-lam)


def fixture_expected_goals(
    team_attack: float,
    team_defence: float,
    opp_attack: float,
    opp_defence: float,
    was_home: bool,
) -> dict[str, float]:
    home_mult = HOME_ADVANTAGE if was_home else 1.0 / HOME_ADVANTAGE
    away_mult = 1.0 / home_mult
    team_xg = float(np.clip(LEAGUE_GOALS_PRIOR * team_attack * opp_defence * home_mult, 0.15, 4.5))
    opp_xg = float(np.clip(LEAGUE_GOALS_PRIOR * opp_attack * team_defence * away_mult, 0.15, 4.5))
    p_cs = float(poisson_zero(opp_xg))
    return {
        "team_xg": team_xg,
        "opp_xg": opp_xg,
        "p_clean_sheet": p_cs,
        "attack_fixture_rating": _scale_rating(team_xg, 0.4, 3.2),
        "defence_fixture_rating": _scale_rating(p_cs, 0.05, 0.55),
    }


def _scale_rating(value: float, lo: float, hi: float) -> float:
    clipped = min(max(value, lo), hi)
    return round(100.0 * (clipped - lo) / (hi - lo), 1)


def attach_fixture_ratings(
    upcoming: pd.DataFrame,
    team_ratings: pd.DataFrame,
    use_xg: bool = False,
) -> pd.DataFrame:
    if team_ratings is None or team_ratings.empty:
        team_ratings = pd.DataFrame(
            columns=[
                "team",
                "attack_rating",
                "defence_rating",
                "xg_attack_rating",
                "xg_defence_rating",
            ]
        )

    own = team_ratings.rename(
        columns={
            "attack_rating": "team_attack_rating",
            "defence_rating": "team_defence_rating",
            "xg_attack_rating": "team_xg_attack_rating",
            "xg_defence_rating": "team_xg_defence_rating",
        }
    )
    opp = team_ratings.rename(
        columns={
            "team": "opp_join_team",
            "attack_rating": "opp_attack_rating",
            "defence_rating": "opp_defence_rating",
            "xg_attack_rating": "opp_xg_attack_rating",
            "xg_defence_rating": "opp_xg_defence_rating",
        }
    )
    merged = upcoming.merge(own, how="left", on="team")
    if "opponent_name" in merged.columns and merged["opponent_name"].notna().any():
        opp_key = "opponent_name"
    else:
        opp_key = "opponent_team"
    left = merged[opp_key].astype(str)
    right = opp["opp_join_team"].astype(str)
    merged = merged.assign(_opp_join=left)
    opp = opp.assign(_opp_join=right)
    merged = merged.merge(opp, how="left", on="_opp_join")

    attack_col = "team_xg_attack_rating" if use_xg else "team_attack_rating"
    defence_col = "team_xg_defence_rating" if use_xg else "team_defence_rating"
    opp_attack_col = "opp_xg_attack_rating" if use_xg else "opp_attack_rating"
    opp_defence_col = "opp_xg_defence_rating" if use_xg else "opp_defence_rating"

    records = []
    for _, row in merged.iterrows():
        records.append(
            fixture_expected_goals(
                float(row[attack_col] if pd.notna(row.get(attack_col)) else 1.0),
                float(row[defence_col] if pd.notna(row.get(defence_col)) else 1.0),
                float(row[opp_attack_col] if pd.notna(row.get(opp_attack_col)) else 1.0),
                float(row[opp_defence_col] if pd.notna(row.get(opp_defence_col)) else 1.0),
                bool(row.get("was_home", True)),
            )
        )
    return pd.concat([merged.reset_index(drop=True), pd.DataFrame.from_records(records)], axis=1)
