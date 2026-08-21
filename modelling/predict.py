from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from modelling.scoring import (
    appearance_points,
    gc_deduction,
    load_scoring_rules,
    position_cs_points,
    position_defcon_points,
    position_goal_points,
    save_points,
)


POSITION_PP90_PRIOR = {"GKP": 3.8, "DEF": 3.4, "MID": 4.0, "FWD": 4.6}
MODEL_VERSION = "0.1.1"
FEATURE_VERSION = "0.1.0"

# Model D only. Official CS is still 4 FPL points in scoring_rules.yaml.
# Independent Poisson exp(-opp_xg) with opp_xg floored at 0.15 implies ~86% CS,
# which PL teams do not hit. Shrink toward the league CS rate and cap.
LEAGUE_CS_RATE = 0.28
CS_POISSON_SHRINK = 0.55
CS_PROB_CAP = 0.42
FULL_FORM_BLEND = 0.40
DEFCON_SHRINK = 0.75


@dataclass(frozen=True)
class ModelSpec:
    key: str
    name: str
    use_fixture: bool
    use_xg: bool
    use_full: bool
    include_h2h: bool = False


MODEL_A = ModelSpec("A", "Model A - Form", False, False, False)
MODEL_B = ModelSpec("B", "Model B - Form + Fixture", True, False, False)
MODEL_C = ModelSpec("C", "Model C - Form + Fixture + xG", True, True, False)
MODEL_D = ModelSpec("D", "Model D - Full Model", True, True, True, True)
MODEL_D_NO_H2H = ModelSpec("D_no_h2h", "Model D - Full without H2H", True, True, True, False)

ALL_MODELS = [MODEL_A, MODEL_B, MODEL_C, MODEL_D]


def _num(row: pd.Series, key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def weighted_pp90(row: pd.Series) -> float:
    prior = POSITION_PP90_PRIOR.get(str(row.get("position", "MID")), 4.0)
    minutes_sample = _num(row, "minutes_l8")
    n = _num(row, "minutes_prev_matches")
    if minutes_sample < 90:
        return prior
    parts = []
    weights = []
    for col, weight in (("pp90_l3", 0.5), ("pp90_l5", 0.3), ("pp90_l8", 0.2)):
        value = row.get(col)
        if value is not None and not (isinstance(value, float) and np.isnan(value)):
            parts.append(float(np.clip(value, 0.0, 12.0)))
            weights.append(weight)
    if not parts:
        return prior
    observed = float(np.average(parts, weights=weights))
    shrink = minutes_sample / (minutes_sample + 270.0)
    return (1 - shrink) * prior + shrink * observed


def calibrate_clean_sheet_prob(p_cs: float) -> float:
    """Shrink a Poisson CS probability toward the observed PL rate. Does not change FPL CS points."""
    raw = float(np.clip(p_cs, 0.0, 0.95))
    shrunk = LEAGUE_CS_RATE + CS_POISSON_SHRINK * (raw - LEAGUE_CS_RATE)
    return float(np.clip(shrunk, 0.05, CS_PROB_CAP))


def _fixture_adjusted_form(row: pd.Series, position: str, form_xpts: float) -> float:
    attack_adj = 0.75 + 0.5 * (_num(row, "attack_fixture_rating", 50) / 100.0)
    defence_adj = 0.85 + 0.3 * (_num(row, "defence_fixture_rating", 50) / 100.0)
    if position in {"GKP", "DEF"}:
        return form_xpts * (0.55 * attack_adj + 0.45 * defence_adj)
    if position == "MID":
        return form_xpts * (0.75 * attack_adj + 0.25 * defence_adj)
    return form_xpts * (0.9 * attack_adj + 0.1 * defence_adj)


def player_share(row: pd.Series, player_col: str, team_col: str, default: float) -> float:
    player = _num(row, player_col)
    team_mean = _num(row, team_col)
    n = min(8.0, max(_num(row, "minutes_prev_matches"), 1.0))
    team_sum = team_mean * n if team_mean <= 15 else team_mean
    if team_sum <= 0:
        return default
    return float(np.clip(player / team_sum, 0.01, 0.6))


def explain_prediction(row: pd.Series, spec: ModelSpec, xpts: float, components: dict) -> dict:
    positives = []
    negatives = []
    if _num(row, "start_probability") >= 0.8:
        positives.append("High projected start probability")
    if _num(row, "expected_minutes") < 45:
        negatives.append("Low expected minutes")
    if spec.use_fixture:
        if _num(row, "attack_fixture_rating") >= 70:
            positives.append("Strong attacking fixture rating")
        if _num(row, "attack_fixture_rating") <= 30:
            negatives.append("Difficult attacking fixture")
        if _num(row, "defence_fixture_rating") >= 70:
            positives.append("Strong clean-sheet opportunity")
        if _num(row, "defence_fixture_rating") <= 30:
            negatives.append("Difficult defensive fixture")
        if bool(row.get("was_home", False)):
            positives.append("Home fixture")
        else:
            negatives.append("Away fixture")
    if spec.use_xg:
        if _num(row, "xg90_l5") >= 0.4:
            positives.append("Strong recent xG/90")
        if _num(row, "xa90_l5") >= 0.3:
            positives.append("Strong recent xA/90")
    if spec.use_full and _num(row, "n_meetings") >= 4:
        positives.append("Historical H2H included with low weight")
    return {
        "xpts": round(xpts, 3),
        "model": spec.name,
        "name": row.get("name"),
        "team": row.get("team"),
        "position": row.get("position"),
        "positives": positives,
        "negatives": negatives,
        "components": components,
    }


def predict_row(row: pd.Series, spec: ModelSpec, rules: dict | None = None) -> dict:
    rules = rules or load_scoring_rules()
    position = str(row.get("position") or "MID")
    exp_min = _num(row, "expected_minutes", 0.0)
    p_start = _num(row, "start_probability", 0.0)
    p_60 = _num(row, "p_60", 0.0)
    if exp_min <= 0:
        return _pack(row, spec, 0.0, {"appearance": 0.0, "form_projection": 0.0})
    pp90 = weighted_pp90(row)
    form_xpts = exp_min / 90.0 * pp90

    if not spec.use_fixture:
        components = {
            "appearance": round(appearance_points(rules, exp_min, p_start, p_60), 3),
            "form_projection": round(form_xpts, 3),
            "goals": 0.0,
            "assists": 0.0,
            "clean_sheet": 0.0,
            "saves": 0.0,
            "defensive_contribution": 0.0,
            "bonus": 0.0,
            "other": 0.0,
        }
        # Blend appearance-aware form rather than double-counting appearance.
        xpts = form_xpts
        return _pack(row, spec, xpts, components)

    team_xg = _num(row, "team_xg_h2h" if spec.include_h2h else "team_xg", _num(row, "team_xg", 1.35))
    p_cs_raw = _num(row, "p_clean_sheet", 0.25)
    p_cs = calibrate_clean_sheet_prob(p_cs_raw) if spec.use_full else p_cs_raw
    opp_xg = _num(row, "opp_xg", 1.35)

    if spec.use_xg:
        goal_share = player_share(row, "expected_goals_l8", "team_xg_l8", 0.08 if position == "FWD" else 0.05)
        assist_share = player_share(row, "expected_assists_l8", "team_xg_l8", 0.07)
        e_goals = team_xg * goal_share * (exp_min / 90.0)
        e_assists = team_xg * assist_share * (exp_min / 90.0)
    else:
        goal_share = player_share(row, "goals_scored_l8", "team_goals_for_l8", 0.08 if position == "FWD" else 0.04)
        assist_share = player_share(row, "assists_l8", "team_goals_for_l8", 0.07)
        e_goals = team_xg * goal_share * (exp_min / 90.0)
        e_assists = team_xg * assist_share * (exp_min / 90.0)

    e_saves = 0.0
    if position == "GKP":
        saves_l5 = _num(row, "saves_l5")
        mins_l5 = max(_num(row, "minutes_l5"), 1)
        e_saves = saves_l5 / mins_l5 * exp_min

    defcon_rate = 0.0
    if position != "GKP":
        dc_l5 = _num(row, "defensive_contribution_l5")
        n5 = min(5, max(_num(row, "minutes_prev_matches"), 1))
        defcon_rate = dc_l5 / n5
        # historical defensive_contribution is already FPL points (0 or 2), so rate is points/game
    bonus_rate = _num(row, "bonus_l5") / max(min(5, _num(row, "minutes_prev_matches")), 1)
    yellow_rate = _num(row, "yellow_cards_l8") / max(min(8, _num(row, "minutes_prev_matches")), 1)

    appearance = appearance_points(rules, exp_min, p_start, p_60)
    goals = e_goals * position_goal_points(rules, position)
    assists = e_assists * float(rules["assists"])
    clean_sheet = p_cs * p_60 * position_cs_points(rules, position)
    saves = save_points(rules, e_saves) if position == "GKP" else 0.0
    gc = gc_deduction(rules, position, opp_xg, p_60)
    if not spec.use_full:
        defcon = 0.0
    else:
        # Historical defensive_contribution is already FPL points (0 or 2). Shrink because last-5 overfits.
        defcon = min(float(position_defcon_points(rules, position)), defcon_rate) * p_60 * DEFCON_SHRINK
    bonus = bonus_rate * p_60
    cards = yellow_rate * p_start * float(rules["yellow_cards"])
    form_adj = _fixture_adjusted_form(row, position, form_xpts)
    component_xpts = appearance + goals + assists + clean_sheet + saves + gc + defcon + bonus + cards

    if spec.use_full:
        xpts = FULL_FORM_BLEND * form_adj + (1.0 - FULL_FORM_BLEND) * component_xpts
    else:
        xpts = 0.65 * form_adj + 0.35 * (appearance + goals + assists + clean_sheet + saves + gc)

    components = {
        "appearance": round(appearance, 3),
        "goals": round(goals, 3),
        "assists": round(assists, 3),
        "clean_sheet": round(clean_sheet, 3),
        "saves": round(saves, 3),
        "goals_conceded": round(gc, 3),
        "defensive_contribution": round(defcon, 3),
        "bonus": round(bonus, 3),
        "cards": round(cards, 3),
        "form_projection": round(form_xpts, 3),
    }
    xpts = float(np.clip(max(xpts, 0.0), 0.0, 18.0))
    return _pack(row, spec, xpts, components)


def _pack(row: pd.Series, spec: ModelSpec, xpts: float, components: dict) -> dict:
    return {
        "element": int(row["element"]),
        "GW": int(row["GW"]),
        "name": row.get("name"),
        "team": row.get("team"),
        "position": row.get("position"),
        "model_key": spec.key,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "xpts": round(float(xpts), 4),
        "expected_minutes": round(_num(row, "expected_minutes"), 2),
        "start_probability": round(_num(row, "start_probability"), 3),
        "attack_fixture_rating": row.get("attack_fixture_rating"),
        "defence_fixture_rating": row.get("defence_fixture_rating"),
        "components": components,
        "explanation": explain_prediction(row, spec, xpts, components),
    }


def predict_frame(features: pd.DataFrame, spec: ModelSpec, rules: dict | None = None) -> pd.DataFrame:
    rules = rules or load_scoring_rules()
    if features.empty:
        return pd.DataFrame()
    rows = [predict_row(row, spec, rules) for _, row in features.iterrows()]
    preds = pd.DataFrame(rows)
    grouped = preds.groupby(["element", "GW", "model_key"], as_index=False).agg(
        {
            "name": "first",
            "team": "first",
            "position": "first",
            "model_version": "first",
            "feature_version": "first",
            "xpts": "sum",
            "expected_minutes": "sum",
            "start_probability": "max",
            "attack_fixture_rating": "mean",
            "defence_fixture_rating": "mean",
            "components": "first",
            "explanation": "first",
        }
    )
    return grouped
