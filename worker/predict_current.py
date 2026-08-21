from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.db.models import ModelRun, PlayerPrediction
from data.clients.fpl_client import FplClient, map_fixture
from data.ingestion.historical import load_merged_gameweeks, remap_elements_to_codes
from features.builder import build_upcoming_features
from features.player_form import add_player_rolling_features, aggregate_player_gameweeks
from features.team_strength import add_team_rolling_ratings, unique_team_matches
from modelling.predict import ALL_MODELS, ModelSpec, predict_frame
from modelling.scoring import load_scoring_rules, load_season_config
from worker.model_league import freeze_model_picks, update_actual_points

POSITION = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
SEASON_ORDER = {"2024-25": 0, "2025-26": 1, "2026-27": 2}


def _upcoming_for_event(elements: list[dict], fixtures: list[dict], event_id: int, team_name: dict, season: str) -> pd.DataFrame:
    rows = []
    event_fx = [fx for fx in fixtures if fx.get("event_id") == event_id]
    for fx in event_fx:
        home, away = fx["home_fpl_team_id"], fx["away_fpl_team_id"]
        for el in elements:
            if el["team"] not in {home, away}:
                continue
            was_home = el["team"] == home
            rows.append(
                {
                    "element": el["id"],
                    "name": el["web_name"],
                    "position": POSITION[el["element_type"]],
                    "team": team_name[el["team"]],
                    "opponent_team": away if was_home else home,
                    "opponent_name": team_name[away if was_home else home],
                    "was_home": was_home,
                    "fixture": fx["fpl_fixture_id"],
                    "GW": event_id,
                    "season": season,
                    "now_cost": el.get("now_cost"),
                    "selected_by_percent": float(el.get("selected_by_percent") or 0),
                    "status": el.get("status") or "a",
                    "news": el.get("news") or "",
                    "chance_of_playing_next_round": el.get("chance_of_playing_next_round"),
                    "short_team": None,
                }
            )
    return pd.DataFrame(rows)


def _availability_scale(row: pd.Series, gw: int, target_gw: int) -> float:
    chance = row.get("chance_of_playing_next_round")
    status = str(row.get("status") or "a")
    if chance is None or (isinstance(chance, float) and pd.isna(chance)) or chance == "":
        if status in {"i", "s", "u"}:
            chance = 0.0
        elif status == "d":
            chance = 50.0
        else:
            chance = 100.0
    chance = float(chance)
    if gw == target_gw:
        return chance / 100.0
    if status in {"i", "s", "u"} and chance <= 25:
        return chance / 100.0
    return max(chance, 75.0) / 100.0 if status == "a" else max(chance, 25.0) / 100.0


def compute_current_predictions(horizon: int = 5) -> dict:
    """Predict next 1/3/5 Gameweeks from live FPL fixtures + historical form."""
    settings = get_settings()
    client = FplClient()
    bootstrap = client.bootstrap_static()
    fixtures = [map_fixture(row) for row in client.fixtures()]
    next_event = next((ev for ev in bootstrap["events"] if ev.get("is_next") or ev.get("is_current")), None)
    if next_event is None:
        raise RuntimeError("Could not determine current/next Gameweek")
    target_gw = int(next_event["id"])
    teams = pd.DataFrame([{"id": t["id"], "name": t["name"], "short_name": t["short_name"]} for t in bootstrap["teams"]])
    team_name = dict(zip(teams["id"], teams["name"]))
    team_short = dict(zip(teams["id"], teams["short_name"]))

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

    history["timeline"] = history["season"].map(SEASON_ORDER).fillna(0).astype(int) * 100 + history["GW"].astype(int)
    cutoff = SEASON_ORDER[settings.current_season] * 100 + target_gw
    promoted = set(load_season_config().get("seasons", {}).get(settings.current_season, {}).get("promoted", []))
    pre_pgw = add_player_rolling_features(aggregate_player_gameweeks(history), exclude_current_row=False)
    pre_teams = add_team_rolling_ratings(unique_team_matches(history), promoted_teams=promoted)
    rules = load_scoring_rules()

    live = {el["id"]: el for el in bootstrap["elements"]}
    frames: dict[str, pd.DataFrame] = {}
    for spec in ALL_MODELS:
        gw_parts = []
        for gw in range(target_gw, target_gw + horizon):
            upcoming = _upcoming_for_event(bootstrap["elements"], fixtures, gw, team_name, settings.current_season)
            if upcoming.empty:
                continue
            upcoming["timeline"] = SEASON_ORDER[settings.current_season] * 100 + gw
            features = build_upcoming_features(
                history=history,
                upcoming=upcoming,
                teams=teams,
                season=settings.current_season,
                use_xg_ratings=spec.use_xg,
                include_h2h=spec.include_h2h,
                precomputed_pgw=pre_pgw,
                precomputed_team_ratings=pre_teams,
                timeline_cutoff=cutoff,
            )
            scale = features.apply(lambda row: _availability_scale(row, gw, target_gw), axis=1)
            features["expected_minutes"] = features["expected_minutes"] * scale
            features["start_probability"] = features["start_probability"] * scale
            preds = predict_frame(features, spec, rules)
            preds["horizon_gw"] = gw
            meta_cols = [
                c
                for c in [
                    "element",
                    "now_cost",
                    "selected_by_percent",
                    "status",
                    "news",
                    "chance_of_playing_next_round",
                    "opponent_name",
                    "was_home",
                ]
                if c in features.columns or c in upcoming.columns
            ]
            meta = upcoming.drop_duplicates("element")
            extra = features.drop_duplicates("element")
            for col in ("opponent_name", "was_home"):
                if col in extra.columns and col not in meta.columns:
                    meta = meta.merge(extra[["element", col]], on="element", how="left")
            preds = preds.merge(meta[[c for c in meta_cols if c in meta.columns]], on="element", how="left")
            gw_parts.append(preds)
        if not gw_parts:
            continue
        all_gw = pd.concat(gw_parts, ignore_index=True)
        gw1 = all_gw[all_gw["horizon_gw"] == target_gw].copy()
        x3 = all_gw[all_gw["horizon_gw"] < target_gw + 3].groupby("element")["xpts"].sum().rename("xpts_3gw")
        x5 = all_gw[all_gw["horizon_gw"] < target_gw + 5].groupby("element")["xpts"].sum().rename("xpts_5gw")
        gw1 = gw1.merge(x3, on="element", how="left").merge(x5, on="element", how="left")
        gw1["xpts_gw"] = gw1["xpts"]
        gw1["value_score"] = gw1["xpts_3gw"] / (gw1["now_cost"] / 10.0).clip(lower=4.0)
        gw1["differential_score"] = gw1["xpts_gw"] * (1.0 - (gw1["selected_by_percent"].fillna(0) / 100.0).clip(upper=0.4) / 0.4)
        gw1.loc[gw1["xpts_gw"] < 3.5, "differential_score"] = 0
        frames[spec.key] = gw1.sort_values("xpts_gw", ascending=False).reset_index(drop=True)
    return {
        "target_gw": target_gw,
        "deadline": next_event.get("deadline_time"),
        "season": settings.current_season,
        "frames": frames,
        "teams": teams,
        "team_short": team_short,
        "live": live,
        "fixtures": fixtures,
    }


def persist_predictions(session: Session, result: dict) -> list[dict]:
    settings = get_settings()
    published = []
    now = datetime.now(timezone.utc)
    for spec in ALL_MODELS:
        frame = result["frames"].get(spec.key)
        if frame is None or frame.empty:
            continue
        run = ModelRun(
            started_at=now,
            finished_at=now,
            season=result["season"],
            target_event_id=result["target_gw"],
            model_key=spec.key,
            model_version=settings.model_version,
            feature_version=settings.feature_version,
            data_cutoff=now,
            frozen=False,
            status="completed",
            metrics={"n": int(len(frame))},
        )
        session.add(run)
        session.flush()
        for _, row in frame.iterrows():
            explanation = row.get("explanation") if isinstance(row.get("explanation"), dict) else {}
            explanation = {
                **explanation,
                "name": row.get("name"),
                "team": row.get("team"),
                "position": row.get("position"),
                "now_cost": _float_or_none(row.get("now_cost")),
                "selected_by_percent": _float_or_none(row.get("selected_by_percent")),
                "status": row.get("status"),
                "opponent": row.get("opponent_name"),
                "was_home": bool(row.get("was_home")) if pd.notna(row.get("was_home")) else None,
                "value_score": _float_or_none(row.get("value_score")),
            }
            session.add(
                PlayerPrediction(
                    model_run_id=run.id,
                    season=result["season"],
                    fpl_element_id=int(row["element"]),
                    event_id=int(result["target_gw"]),
                    xpts_gw=float(row["xpts_gw"]),
                    xpts_3gw=_float_or_none(row.get("xpts_3gw")),
                    xpts_5gw=_float_or_none(row.get("xpts_5gw")),
                    expected_minutes=float(row.get("expected_minutes") or 0),
                    start_probability=float(row.get("start_probability") or 0),
                    attack_fixture_rating=_float_or_none(row.get("attack_fixture_rating")),
                    defence_fixture_rating=_float_or_none(row.get("defence_fixture_rating")),
                    components=row.get("components") if isinstance(row.get("components"), dict) else None,
                    explanation=explanation,
                    frozen=False,
                )
            )
        published.append({"model": spec.key, "n": int(len(frame)), "run_id": run.id})
    session.commit()
    return published


def generate_current_predictions(session: Session) -> dict:
    result = compute_current_predictions()
    published = persist_predictions(session, result)
    frozen = freeze_model_picks(session, result)
    scored = update_actual_points(session, event_id=result["target_gw"])
    report = write_prediction_report(result)
    return {
        "models": published,
        "target_gw": result["target_gw"],
        "report": str(report),
        "league_frozen": frozen,
        "league_scored": scored,
    }


def write_prediction_report(result: dict, path: Path | None = None) -> Path:
    settings = get_settings()
    path = path or (settings.report_dir / f"gw{result['target_gw']}_{result['season']}_predictions.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    docs_path = Path("docs") / f"PREDICTIONS_{result['season'].replace('-', '_')}_GW{result['target_gw']}.md"
    b = result["frames"].get("B")
    d = result["frames"].get("D")
    primary = b if b is not None else next(iter(result["frames"].values()))
    lines = [
        f"# {result['season']} Gameweek {result['target_gw']} predictions",
        "",
        f"Deadline: {result.get('deadline')}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "Primary xPts and captain: **Model B** (best 2025/26 MAE). Model D still over-weights clean sheets, so it is shown for ranking research only.",
        "3GW/5GW totals are summed fixture-level predictions, including blanks and doubles.",
        "End-of-season rest is not treated as an injury for Gameweeks 1–2.",
        "",
        "## Best picks (Model B xPts)",
        "",
    ]
    lines.extend(_category_lines(primary, d if d is not None else primary))
    playable = primary[primary["expected_minutes"].fillna(0) >= 30].head(20)
    lines.extend(["", "## Model B top 20 this week", "", _table(playable)])
    if d is not None:
        caps = d[d["expected_minutes"].fillna(0) >= 45].head(15)
        lines.extend(
            [
                "",
                "## Model D ranking",
                "",
                _table(caps, cols=("name", "team", "position", "xpts_gw", "xpts_3gw", "start_probability")),
            ]
        )
    for key, frame in result["frames"].items():
        csv_path = path.with_name(f"gw{result['target_gw']}_model_{key}.csv")
        export_cols = [c for c in ["element", "name", "team", "position", "xpts_gw", "xpts_3gw", "xpts_5gw", "expected_minutes", "start_probability", "attack_fixture_rating", "defence_fixture_rating", "now_cost", "selected_by_percent", "status", "value_score"] if c in frame.columns]
        frame[export_cols].to_csv(csv_path, index=False)
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    docs_path.write_text(text, encoding="utf-8")
    return docs_path


def category_records(primary: pd.DataFrame) -> list[dict]:
    settings = get_settings()
    available = primary[
        primary["status"].fillna("a").isin(["a", "d"])
        & (primary["expected_minutes"].fillna(0) >= 30)
    ].copy()

    def pick(frame, mask=None, sort="xpts_gw"):
        subset = frame if mask is None else frame[mask]
        if subset.empty:
            return None
        return subset.sort_values(sort, ascending=False).iloc[0]

    cap_pool = available[available["expected_minutes"].fillna(0) >= 45]
    vc = cap_pool.sort_values("xpts_gw", ascending=False)
    diffs = available[
        (available["selected_by_percent"] < settings.differential_ownership_max) & (available["xpts_gw"] >= 3.5)
    ]
    ultra = available[
        (available["selected_by_percent"] < settings.ultra_differential_ownership_max) & (available["xpts_gw"] >= 3.5)
    ]
    budget = available[available["now_cost"].fillna(999) <= 50]
    cats = [
        ("Best overall", pick(available)),
        ("Best captain", pick(cap_pool)),
        ("Best vice-captain", vc.iloc[1] if len(vc) > 1 else pick(cap_pool)),
        ("Best value 3GW", pick(available, sort="value_score")),
        ("Best differential <10%", pick(diffs) if not diffs.empty else None),
        ("Best ultra differential <5%", pick(ultra) if not ultra.empty else None),
        ("Best GK", pick(available, available["position"] == "GKP")),
        ("Best defender", pick(available, available["position"] == "DEF")),
        ("Best midfielder", pick(available, available["position"] == "MID")),
        ("Best forward", pick(available, available["position"] == "FWD")),
        ("Best budget GK", pick(budget, budget["position"] == "GKP")),
        ("Best budget defender", pick(budget, budget["position"] == "DEF")),
        ("Best budget midfielder", pick(budget, budget["position"] == "MID")),
        ("Best budget forward", pick(budget, budget["position"] == "FWD")),
        ("Best one-week punt", pick(available, sort="xpts_gw")),
        ("Best 3GW transfer", pick(available, sort="xpts_3gw")),
        ("Best 5GW transfer", pick(available, sort="xpts_5gw")),
    ]
    out = []
    for label, row in cats:
        if row is None:
            out.append({"category": label, "player": None})
            continue
        out.append(
            {
                "category": label,
                "element": int(row["element"]),
                "name": row["name"],
                "team": row["team"],
                "position": row["position"],
                "xpts_gw": round(float(row["xpts_gw"]), 2),
                "xpts_3gw": round(float(row.get("xpts_3gw") or 0), 2),
                "xpts_5gw": round(float(row.get("xpts_5gw") or 0), 2),
                "ownership": round(float(row.get("selected_by_percent") or 0), 1),
                "price": round(float(row.get("now_cost") or 0) / 10.0, 1),
                "expected_minutes": round(float(row.get("expected_minutes") or 0), 1),
            }
        )
    return out


def _category_lines(primary: pd.DataFrame, captain_frame: pd.DataFrame) -> list[str]:
    del captain_frame
    lines = ["| Category | Player | Team | Pos | GW xPts | 3GW | 5GW | Own% | Price |", "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in category_records(primary):
        if not row.get("name"):
            lines.append(f"| {row['category']} | n/a | | | | | | | |")
            continue
        lines.append(
            f"| {row['category']} | {row['name']} | {row['team']} | {row['position']} | {row['xpts_gw']:.2f} | {row['xpts_3gw']:.2f} | {row['xpts_5gw']:.2f} | {row['ownership']:.1f} | £{row['price']:.1f} |"
        )
    return lines


def _table(frame: pd.DataFrame, cols=None) -> str:
    cols = cols or ("name", "team", "position", "xpts_gw", "xpts_3gw", "xpts_5gw", "expected_minutes", "selected_by_percent")
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = [header, sep]
    for _, row in frame.iterrows():
        cells = []
        for col in cols:
            val = row.get(col)
            if col.startswith("xpts") or col == "expected_minutes":
                cells.append(f"{float(val):.2f}" if pd.notna(val) else "")
            elif col == "selected_by_percent":
                cells.append(f"{float(val):.1f}" if pd.notna(val) else "")
            elif col == "start_probability":
                cells.append(f"{float(val):.2f}" if pd.notna(val) else "")
            else:
                cells.append(str(val))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def _float_or_none(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
