from __future__ import annotations

import pandas as pd

from modelling.predict import (
    CS_PROB_CAP,
    MODEL_C,
    MODEL_D,
    calibrate_clean_sheet_prob,
    predict_row,
)


def test_poisson_cs_is_shrunk_and_capped():
    assert calibrate_clean_sheet_prob(0.86) == CS_PROB_CAP
    assert calibrate_clean_sheet_prob(0.28) == 0.28
    mid = calibrate_clean_sheet_prob(0.50)
    assert 0.28 < mid < 0.50


def _defender(p_cs: float) -> pd.Series:
    return pd.Series(
        {
            "element": 1,
            "GW": 1,
            "name": "Back",
            "team": "Brighton",
            "position": "DEF",
            "expected_minutes": 90,
            "start_probability": 0.99,
            "p_60": 0.99,
            "p_clean_sheet": p_cs,
            "opp_xg": 0.2,
            "team_xg": 1.2,
            "attack_fixture_rating": 50,
            "defence_fixture_rating": 90,
            "minutes_l8": 720,
            "pp90_l3": 3.0,
            "pp90_l5": 3.0,
            "pp90_l8": 3.0,
            "minutes_prev_matches": 8,
            "expected_goals_l8": 0.2,
            "expected_assists_l8": 0.3,
            "team_xg_l8": 10.0,
            "defensive_contribution_l5": 8.0,
            "bonus_l5": 2.0,
            "yellow_cards_l8": 1.0,
            "was_home": True,
        }
    )


def test_model_d_does_not_pay_full_poisson_cs_to_defenders():
    raw = 0.85
    pred = predict_row(_defender(raw), MODEL_D)
    uncalibrated = raw * 0.99 * 4
    assert pred["components"]["clean_sheet"] < uncalibrated - 1.0
    assert pred["components"]["clean_sheet"] == round(CS_PROB_CAP * 0.99 * 4, 3)


def test_model_c_keeps_raw_poisson_cs():
    raw = 0.85
    pred = predict_row(_defender(raw), MODEL_C)
    assert pred["components"]["clean_sheet"] == round(raw * 0.99 * 4, 3)
