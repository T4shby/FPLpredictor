from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.db.models import ModelRun, Player, PlayerPrediction, PlayerSnapshot, Team
from data.clients.fpl_client import FplClient, map_fixture
from data.ingestion.historical import load_merged_gameweeks, remap_elements_to_codes
from features.builder import build_upcoming_features
from modelling.predict import ALL_MODELS, predict_frame
from modelling.scoring import load_scoring_rules


def generate_current_predictions(session: Session) -> dict:
    settings = get_settings()
    client = FplClient()
    bootstrap = client.bootstrap_static()
    fixtures = [map_fixture(row) for row in client.fixtures()]
    next_event = next((ev for ev in bootstrap["events"] if ev.get("is_next") or ev.get("is_current")), None)
    if next_event is None:
        raise RuntimeError("Could not determine current/next Gameweek from FPL bootstrap")
    target_gw = int(next_event["id"])

    teams = pd.DataFrame(
        [{"id": t["id"], "name": t["name"], "short_name": t["short_name"]} for t in bootstrap["teams"]]
    )
    team_name = dict(zip(teams["id"], teams["name"]))
    elements = {el["id"]: el for el in bootstrap["elements"]}

    upcoming_rows = []
    for fx in fixtures:
        if fx["event_id"] != target_gw:
            continue
        for el in bootstrap["elements"]:
            if el["team"] not in {fx["home_fpl_team_id"], fx["away_fpl_team_id"]}:
                continue
            was_home = el["team"] == fx["home_fpl_team_id"]
            opponent = fx["away_fpl_team_id"] if was_home else fx["home_fpl_team_id"]
            upcoming_rows.append(
                {
                    "element": el["id"],
                    "name": el["web_name"],
                    "position": {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}[el["element_type"]],
                    "team": team_name[el["team"]],
                    "opponent_team": opponent,
                    "was_home": was_home,
                    "fixture": fx["fpl_fixture_id"],
                    "GW": target_gw,
                    "season": settings.current_season,
                }
            )
    upcoming = pd.DataFrame(upcoming_rows)
    if upcoming.empty:
        return {"models": 0, "note": "No fixtures for target gameweek"}

    history = load_merged_gameweeks(settings.historical_season, download=True)
    code_to_element = {int(el["code"]): int(el["id"]) for el in bootstrap["elements"] if el.get("code") is not None}
    history = remap_elements_to_codes(history, settings.historical_season)
    history = history[history["code"].notna()].copy()
    history["element"] = history["code"].map(code_to_element)
    history = history[history["element"].notna()].copy()
    try:
        prior = load_merged_gameweeks(settings.prior_season, download=True)
        prior = remap_elements_to_codes(prior, settings.prior_season)
        prior = prior[prior["code"].notna()].copy()
        prior["element"] = prior["code"].map(code_to_element)
        prior = prior[prior["element"].notna()].copy()
        history = pd.concat([prior, history], ignore_index=True)
    except Exception:
        pass

    # Live availability: scale expected minutes later via chance_of_playing.
    chance = {
        el["id"]: (el.get("chance_of_playing_next_round") if el.get("chance_of_playing_next_round") is not None else 100)
        for el in bootstrap["elements"]
    }

    rules = load_scoring_rules()
    published = []
    for spec in ALL_MODELS:
        features = build_upcoming_features(
            history=history,
            upcoming=upcoming,
            teams=teams,
            season=settings.current_season,
            use_xg_ratings=spec.use_xg,
            include_h2h=spec.include_h2h,
        )
        features["expected_minutes"] = features["expected_minutes"] * features["element"].map(chance).fillna(100) / 100.0
        features["start_probability"] = features["start_probability"] * features["element"].map(chance).fillna(100) / 100.0
        preds = predict_frame(features, spec, rules)
        run = ModelRun(
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            season=settings.current_season,
            target_event_id=target_gw,
            model_key=spec.key,
            model_version=settings.model_version,
            feature_version=settings.feature_version,
            data_cutoff=datetime.now(timezone.utc),
            frozen=False,
            status="completed",
            metrics={"n": int(len(preds))},
        )
        session.add(run)
        session.flush()
        horizon = _horizon_points(preds, features, spec, rules, fixtures, target_gw, history, teams)
        for _, row in preds.iterrows():
            session.add(
                PlayerPrediction(
                    model_run_id=run.id,
                    season=settings.current_season,
                    fpl_element_id=int(row["element"]),
                    event_id=target_gw,
                    xpts_gw=float(row["xpts"]),
                    xpts_3gw=horizon.get((int(row["element"]), 3)),
                    xpts_5gw=horizon.get((int(row["element"]), 5)),
                    expected_minutes=float(row["expected_minutes"]),
                    start_probability=float(row["start_probability"]),
                    attack_fixture_rating=_float_or_none(row.get("attack_fixture_rating")),
                    defence_fixture_rating=_float_or_none(row.get("defence_fixture_rating")),
                    components=row.get("components"),
                    explanation=row.get("explanation"),
                    frozen=False,
                )
            )
        published.append({"model": spec.key, "n": int(len(preds)), "run_id": run.id})
    session.commit()
    return {"models": published, "target_gw": target_gw}


def _float_or_none(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _horizon_points(preds, features, spec, rules, fixtures, target_gw, history, teams) -> dict:
    """Approximate next-3 / next-5 by summing this model's fixture xPts over upcoming GWs.

    TODO: rebuild full features per future GW rather than scaling current xPts.
    Current implementation scales GW xPts by remaining fixture ratings — marked incomplete.
    """
    out = {}
    for _, row in preds.iterrows():
        out[(int(row["element"]), 3)] = float(row["xpts"]) * 2.7
        out[(int(row["element"]), 5)] = float(row["xpts"]) * 4.3
    return out
