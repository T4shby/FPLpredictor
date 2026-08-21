from __future__ import annotations

import numpy as np
import pandas as pd

from features.player_form import annotate_team_goals


PROMOTED_ATTACK_PRIOR = 0.85
PROMOTED_DEFENCE_PRIOR = 1.15
LEAGUE_GOALS_PRIOR = 1.35
PRIOR_STRENGTH = 8.0


def unique_team_matches(df: pd.DataFrame) -> pd.DataFrame:
    work = annotate_team_goals(df)
    if "opponent_name" in work.columns:
        work = work.copy()
        work["opponent_team"] = work["opponent_name"].where(work["opponent_name"].notna(), work.get("opponent_team"))
    if "fixture" in work.columns:
        keys = ["season", "GW", "team", "fixture"]
    else:
        keys = ["season", "GW", "team", "opponent_team"]
    keep = [
        col
        for col in [
            "season",
            "GW",
            "team",
            "opponent_team",
            "was_home",
            "fixture",
            "team_goals_for",
            "team_goals_against",
            "expected_goals",
            "expected_goals_conceded",
            "timeline",
        ]
        if col in work.columns
    ]
    team = work[keep].copy()
    team["team_xg"] = work["expected_goals"] if "expected_goals" in work.columns else 0
    team["team_xgc"] = work["expected_goals_conceded"] if "expected_goals_conceded" in work.columns else 0
    grouped = team.groupby([c for c in keys if c in team.columns], as_index=False)
    named = dict(
        opponent_team=("opponent_team", "first") if "opponent_team" in team.columns else ("team", "first"),
        was_home=("was_home", "first"),
        team_goals_for=("team_goals_for", "first"),
        team_goals_against=("team_goals_against", "first"),
        team_xg=("team_xg", "sum"),
        team_xgc=("team_xgc", "mean"),
    )
    if "timeline" in team.columns:
        named["timeline"] = ("timeline", "max")
    agg = grouped.agg(**named)
    return agg.sort_values(["team", "season", "GW"]).reset_index(drop=True)


def add_team_rolling_ratings(
    team_matches: pd.DataFrame,
    promoted_teams: set[str] | None = None,
    windows: tuple[int, ...] = (3, 5, 8),
) -> pd.DataFrame:
    out = team_matches.sort_values(["team", "season", "GW"]).copy()
    promoted_teams = promoted_teams or set()
    grouped = out.groupby("team", sort=False)
    for col in ["team_goals_for", "team_goals_against", "team_xg", "team_xgc"]:
        if col not in out.columns:
            out[col] = 0.0
        for window in windows:
            out[f"{col}_l{window}"] = grouped[col].transform(
                lambda s, w=window: s.rolling(w, min_periods=1).mean()
            )
        out[f"{col}_szn"] = grouped[col].transform(lambda s: s.expanding().mean())
        out[f"{col}_n"] = grouped[col].transform(lambda s: s.notna().cumsum())

    n = out["team_goals_for_n"].fillna(0)
    gf = out["team_goals_for_szn"].fillna(LEAGUE_GOALS_PRIOR)
    ga = out["team_goals_against_szn"].fillna(LEAGUE_GOALS_PRIOR)
    xg = out["team_xg_szn"].fillna(LEAGUE_GOALS_PRIOR)
    xgc = out["team_xgc_szn"].fillna(LEAGUE_GOALS_PRIOR)
    is_promoted = out["team"].isin(promoted_teams)
    attack_prior = np.where(is_promoted, PROMOTED_ATTACK_PRIOR, 1.0)
    defence_prior = np.where(is_promoted, PROMOTED_DEFENCE_PRIOR, 1.0)
    w = n / (n + PRIOR_STRENGTH)
    observed_attack = gf / LEAGUE_GOALS_PRIOR
    observed_defence = ga / LEAGUE_GOALS_PRIOR
    observed_xg_attack = np.where(xg > 0, xg / LEAGUE_GOALS_PRIOR, observed_attack)
    observed_xg_defence = np.where(xgc > 0, xgc / LEAGUE_GOALS_PRIOR, observed_defence)
    out["attack_rating"] = (1 - w) * attack_prior + w * observed_attack
    out["defence_rating"] = (1 - w) * defence_prior + w * observed_defence
    out["xg_attack_rating"] = (1 - w) * attack_prior + w * observed_xg_attack
    out["xg_defence_rating"] = (1 - w) * defence_prior + w * observed_xg_defence
    return out


def latest_team_ratings(team_rated: pd.DataFrame, before_gw: int | None = None, timeline_cutoff: int | None = None) -> pd.DataFrame:
    hist = team_rated
    if timeline_cutoff is not None and "timeline" in team_rated.columns:
        hist = team_rated[team_rated["timeline"] < timeline_cutoff]
    elif before_gw is not None:
        hist = team_rated[team_rated["GW"] < before_gw]
    if hist.empty:
        cols = ["team", "attack_rating", "defence_rating", "xg_attack_rating", "xg_defence_rating"]
        return pd.DataFrame(columns=cols)
    latest = hist.sort_values(["team", "GW"]).groupby("team", as_index=False).tail(1)
    return latest[
        [
            "team",
            "attack_rating",
            "defence_rating",
            "xg_attack_rating",
            "xg_defence_rating",
            "team_goals_for_l8",
            "team_goals_against_l8",
            "team_xg_l8",
            "team_xgc_l8",
        ]
    ]
