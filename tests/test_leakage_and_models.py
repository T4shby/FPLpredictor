from __future__ import annotations

import pandas as pd
import pytest

from features.builder import build_upcoming_features
from features.player_form import add_player_rolling_features, aggregate_player_gameweeks
from modelling.predict import MODEL_A, predict_frame
from modelling.scoring import appearance_points, load_scoring_rules


def _toy_season() -> pd.DataFrame:
    rows = []
    for gw in range(1, 6):
        rows.append(
            {
                "season": "2025-26",
                "element": 1,
                "name": "Spike",
                "position": "FWD",
                "team": "Arsenal",
                "opponent_team": "Leeds",
                "opponent_name": "Leeds",
                "was_home": True,
                "fixture": 100 + gw,
                "GW": gw,
                "minutes": 90,
                "starts": 1,
                "total_points": 20 if gw == 5 else 2,
                "goals_scored": 3 if gw == 5 else 0,
                "assists": 0,
                "clean_sheets": 0,
                "goals_conceded": 1,
                "own_goals": 0,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "saves": 0,
                "bonus": 0,
                "bps": 10,
                "expected_goals": 2.0 if gw == 5 else 0.2,
                "expected_assists": 0.1,
                "expected_goal_involvements": 0.3,
                "expected_goals_conceded": 1.0,
                "defensive_contribution": 0,
                "team_h_score": 3 if gw == 5 else 1,
                "team_a_score": 1,
            }
        )
        rows.append(
            {
                "season": "2025-26",
                "element": 2,
                "name": "Stable",
                "position": "MID",
                "team": "Leeds",
                "opponent_team": "Arsenal",
                "opponent_name": "Arsenal",
                "was_home": False,
                "fixture": 100 + gw,
                "GW": gw,
                "minutes": 90,
                "starts": 1,
                "total_points": 3,
                "goals_scored": 0,
                "assists": 0,
                "clean_sheets": 0,
                "goals_conceded": 1,
                "own_goals": 0,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "saves": 0,
                "bonus": 0,
                "bps": 8,
                "expected_goals": 0.1,
                "expected_assists": 0.1,
                "expected_goal_involvements": 0.2,
                "expected_goals_conceded": 1.2,
                "defensive_contribution": 0,
                "team_h_score": 3 if gw == 5 else 1,
                "team_a_score": 1,
            }
        )
    return pd.DataFrame(rows)


def test_rolling_features_exclude_current_row_when_requested():
    df = _toy_season()
    pgw = add_player_rolling_features(aggregate_player_gameweeks(df), exclude_current_row=True)
    gw5 = pgw[(pgw["element"] == 1) & (pgw["GW"] == 5)].iloc[0]
    assert gw5["total_points_l3"] == 6
    assert gw5["total_points_prev"] == 2


def test_history_builder_cannot_see_target_gameweek_outcomes():
    df = _toy_season()
    history = df[df["GW"] < 5]
    upcoming = df.loc[df["GW"] == 5, ["element", "name", "position", "team", "opponent_team", "opponent_name", "was_home", "fixture", "GW", "season"]]
    features = build_upcoming_features(history, upcoming, season="2025-26")
    spike = features[features["element"] == 1].iloc[0]
    assert spike["total_points_l3"] == 6
    assert spike["expected_goals_l3"] == pytest.approx(0.6)
    assert spike["total_points_szn"] == 8


def test_double_gameweek_points_are_summed_in_actuals():
    from backtest.engine import actuals_by_player_gw

    df = pd.DataFrame(
        [
            {"element": 10, "GW": 33, "total_points": 6, "minutes": 90},
            {"element": 10, "GW": 33, "total_points": 8, "minutes": 70},
        ]
    )
    actuals = actuals_by_player_gw(df)
    assert actuals.iloc[0]["actual_points"] == 14
    assert actuals.iloc[0]["n_fixtures"] == 2


def test_blank_gameweek_has_zero_rows():
    df = _toy_season()
    upcoming = df.loc[df["GW"] == 99]
    features = build_upcoming_features(df[df["GW"] < 5], upcoming)
    assert features.empty


def test_appearance_points_use_config_not_hardcoded_literals():
    rules = load_scoring_rules()
    assert rules["appearance"]["long_play"] == 2
    assert appearance_points(rules, expected_minutes=90, p_start=1, p_60=1) == 2
    assert appearance_points(rules, expected_minutes=20, p_start=0.8, p_60=0) == 0.8


def test_null_playing_chance_is_available():
    import pandas as pd
    from worker.predict_current import _availability_scale

    row = pd.Series({"chance_of_playing_next_round": float("nan"), "status": "a"})
    assert _availability_scale(row, gw=1, target_gw=1) == 1.0
    import pandas as pd
    from modelling.predict import MODEL_A, predict_row

    row = pd.Series(
        {
            "element": 1,
            "GW": 1,
            "name": "Bench",
            "team": "Arsenal",
            "position": "MID",
            "expected_minutes": 0,
            "pp90_l3": 90,
            "minutes_l8": 10,
        }
    )
    assert predict_row(row, MODEL_A)["xpts"] == 0


def test_model_a_returns_predictions_without_using_fixture_columns():
    df = _toy_season()
    history = df[df["GW"] < 4]
    upcoming = df.loc[df["GW"] == 4, ["element", "name", "position", "team", "opponent_team", "was_home", "fixture", "GW", "season"]]
    features = build_upcoming_features(history, upcoming, season="2025-26")
    preds = predict_frame(features, MODEL_A)
    assert set(preds["element"]) == {1, 2}
    assert (preds["xpts"] > 0).all()
