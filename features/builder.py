from __future__ import annotations

import pandas as pd

from features.expected_minutes import expected_minutes_frame
from features.fixture_strength import attach_fixture_ratings
from features.head_to_head import blend_h2h, head_to_head_goals
from features.player_form import add_player_rolling_features, aggregate_player_gameweeks
from features.team_strength import add_team_rolling_ratings, latest_team_ratings, unique_team_matches
from modelling.scoring import load_season_config


def opponent_name_map(teams: pd.DataFrame) -> dict[int, str]:
    if teams is None or teams.empty:
        return {}
    if "id" in teams.columns and "name" in teams.columns:
        return dict(zip(teams["id"].astype(int), teams["name"].astype(str)))
    return {}


def resolve_opponent_names(df: pd.DataFrame, teams: pd.DataFrame | None) -> pd.DataFrame:
    out = df.copy()
    if "opponent_team" not in out.columns:
        out["opponent_name"] = None
        return out
    mapping = opponent_name_map(teams) if teams is not None else {}
    if mapping and pd.api.types.is_numeric_dtype(out["opponent_team"]):
        out["opponent_name"] = out["opponent_team"].map(mapping)
    else:
        out["opponent_name"] = out["opponent_team"]
    return out


def build_upcoming_features(
    history: pd.DataFrame,
    upcoming: pd.DataFrame,
    teams: pd.DataFrame | None = None,
    season: str | None = None,
    use_xg_ratings: bool = False,
    include_h2h: bool = False,
    precomputed_pgw: pd.DataFrame | None = None,
    precomputed_team_ratings: pd.DataFrame | None = None,
    timeline_cutoff: int | None = None,
) -> pd.DataFrame:
    """Leakage-safe features for upcoming fixture rows.

    `history` must contain only Gameweeks strictly before the target Gameweek.
    `upcoming` may include opponent, home/away and identity columns.
    """
    if upcoming.empty:
        return upcoming.copy()

    history = resolve_opponent_names(history, teams) if not history.empty else history
    upcoming = resolve_opponent_names(upcoming, teams)
    upcoming = upcoming.copy()
    upcoming["n_fixtures_upcoming"] = upcoming.groupby(["element", "GW"])["element"].transform("size")

    if history.empty and precomputed_pgw is None:
        latest_players = pd.DataFrame(columns=["element"])
        ratings = pd.DataFrame()
    elif precomputed_pgw is not None:
        pgw = precomputed_pgw
        if timeline_cutoff is not None and "timeline" in pgw.columns:
            pgw = pgw[pgw["timeline"] < timeline_cutoff]
        order_cols = ["element", "timeline"] if "timeline" in pgw.columns else ["element", "season", "GW"]
        latest_players = pgw.sort_values(order_cols).groupby("element", as_index=False).tail(1)
        ratings = precomputed_team_ratings
        if ratings is not None and not ratings.empty:
            ratings = latest_team_ratings(ratings, timeline_cutoff=timeline_cutoff)
        else:
            ratings = pd.DataFrame()
    else:
        # History must already exclude the target Gameweek. Rolling includes
        # the latest historical row, which is the correct as-of-deadline view.
        pgw = add_player_rolling_features(
            aggregate_player_gameweeks(history),
            exclude_current_row=False,
        )
        order_cols = ["element", "timeline"] if "timeline" in pgw.columns else ["element", "season", "GW"]
        latest_players = pgw.sort_values(order_cols).groupby("element", as_index=False).tail(1)
        promoted = set()
        if season:
            promoted = set(load_season_config().get("seasons", {}).get(season, {}).get("promoted", []))
        rated = add_team_rolling_ratings(unique_team_matches(history), promoted_teams=promoted)
        ratings = latest_team_ratings(rated)

    hist_cols = [
        col
        for col in latest_players.columns
        if col not in {"name", "team", "position", "GW", "season", "was_home", "opponent_team", "opponent_name", "n_fixtures"}
    ]
    merged = upcoming.merge(latest_players[hist_cols], on="element", how="left") if not latest_players.empty else upcoming
    fixture_level = attach_fixture_ratings(merged, ratings, use_xg=use_xg_ratings)
    season_start = False
    if "GW" in upcoming.columns and not upcoming.empty:
        season_start = int(pd.to_numeric(upcoming["GW"], errors="coerce").fillna(99).min()) <= 2
    cross_season = False
    if season and not history.empty and "season" in history.columns:
        last_hist_season = str(history.sort_values("timeline" if "timeline" in history.columns else "GW").iloc[-1]["season"])
        cross_season = last_hist_season != str(season)
    fixture_level = expected_minutes_frame(
        fixture_level,
        apply_last_match_injury=not cross_season and not season_start,
    )

    if include_h2h and not history.empty:
        matches = unique_team_matches(history)
        pair = (
            matches.groupby(["team", "opponent_team"], as_index=False)
            .agg(
                n_meetings=("team_goals_for", "size"),
                h2h_goals_for=("team_goals_for", "mean"),
                h2h_goals_against=("team_goals_against", "mean"),
            )
        )
        fixture_level = fixture_level.merge(
            pair,
            how="left",
            left_on=["team", "opponent_name"] if "opponent_name" in fixture_level.columns else ["team", "opponent_team"],
            right_on=["team", "opponent_team"],
            suffixes=("", "_h2hjoin"),
        )
        fixture_level["n_meetings"] = fixture_level["n_meetings"].fillna(0)
        fixture_level["team_xg_h2h"] = [
            blend_h2h(float(x), (None if pd.isna(h) else float(h)), int(n or 0))
            for x, h, n in zip(fixture_level["team_xg"], fixture_level["h2h_goals_for"], fixture_level["n_meetings"])
        ]
    else:
        fixture_level["n_meetings"] = 0
        fixture_level["h2h_goals_for"] = None
        fixture_level["h2h_goals_against"] = None
        fixture_level["team_xg_h2h"] = fixture_level["team_xg"]
    return fixture_level
