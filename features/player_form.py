from __future__ import annotations

import numpy as np
import pandas as pd


PLAYER_SUM_COLS = [
    "minutes",
    "starts",
    "total_points",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "saves",
    "bonus",
    "yellow_cards",
    "expected_goals",
    "expected_assists",
    "expected_goals_conceded",
    "defensive_contribution",
]


def annotate_team_goals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    home_for = pd.to_numeric(out["team_h_score"], errors="coerce").fillna(0) if "team_h_score" in out.columns else 0
    away_for = pd.to_numeric(out["team_a_score"], errors="coerce").fillna(0) if "team_a_score" in out.columns else 0
    was_home = out["was_home"].astype(bool) if "was_home" in out.columns else True
    out["team_goals_for"] = np.where(was_home, home_for, away_for)
    out["team_goals_against"] = np.where(was_home, away_for, home_for)
    return out


def aggregate_player_gameweeks(df: pd.DataFrame) -> pd.DataFrame:
    """One row per player per Gameweek. Double-gameweeks are summed."""
    work = annotate_team_goals(df)
    grouped = work.groupby(["season", "element", "GW"], as_index=False)
    sum_cols = [col for col in PLAYER_SUM_COLS if col in work.columns]
    named = {col: (col, "sum") for col in sum_cols}
    for col, how in [
        ("position", "first"),
        ("team", "first"),
        ("name", "first"),
        ("was_home", "first"),
        ("opponent_team", "first"),
        ("opponent_name", "first"),
        ("timeline", "max"),
        ("value", "last"),
        ("selected", "last"),
        ("kickoff_time", "first"),
    ]:
        if col in work.columns:
            named[col] = (col, how)
    pgw = grouped.agg(**named)
    counts = work.groupby(["season", "element", "GW"]).size().reset_index(name="n_fixtures")
    pgw = pgw.merge(counts, on=["season", "element", "GW"], how="left")
    if "name" not in pgw.columns:
        pgw["name"] = pgw["element"].astype(str)
    return pgw.sort_values(["element", "season", "GW"]).reset_index(drop=True)


def add_player_rolling_features(
    pgw: pd.DataFrame,
    windows: tuple[int, ...] = (3, 5, 8),
    exclude_current_row: bool = False,
) -> pd.DataFrame:
    """Rolling player stats using vectorised groupby rolling, not apply lambdas."""
    out = pgw.sort_values(["element", "season", "GW"]).reset_index(drop=True)
    shift_n = 1 if exclude_current_row else 0
    extras: dict[str, pd.Series] = {}
    grouped = out.groupby("element", sort=False)
    for col in PLAYER_SUM_COLS:
        if col not in out.columns:
            continue
        series = grouped[col].shift(shift_n)
        extras[f"{col}_prev"] = series
        rolled = series.groupby(out["element"], sort=False)
        for window in windows:
            extras[f"{col}_l{window}"] = rolled.rolling(window, min_periods=1).sum().reset_index(level=0, drop=True)
        extras[f"{col}_szn"] = rolled.cumsum()
        extras[f"{col}_prev_matches"] = series.notna().astype(int).groupby(out["element"], sort=False).cumsum()
    extra_df = pd.DataFrame(extras)
    extra_df.index = out.index
    out = pd.concat([out, extra_df], axis=1)
    for window in ("prev", "l3", "l5", "l8"):
        mins = out.get(f"minutes_{window}", pd.Series(0, index=out.index)).fillna(0)
        pts = out.get(f"total_points_{window}", pd.Series(0, index=out.index)).fillna(0)
        xg = out.get(f"expected_goals_{window}", pd.Series(0, index=out.index)).fillna(0)
        xa = out.get(f"expected_assists_{window}", pd.Series(0, index=out.index)).fillna(0)
        out[f"pp90_{window}"] = np.where(mins > 0, pts / mins * 90.0, np.nan)
        out[f"xg90_{window}"] = np.where(mins > 0, xg / mins * 90.0, np.nan)
        out[f"xa90_{window}"] = np.where(mins > 0, xa / mins * 90.0, np.nan)
    return out
