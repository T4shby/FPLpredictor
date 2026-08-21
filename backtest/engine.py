from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from backend.app.core.settings import get_settings
from backtest.metrics import summarise_model
from data.ingestion.historical import load_merged_gameweeks, load_player_codes, load_teams, remap_elements_to_codes
from features.builder import build_upcoming_features, resolve_opponent_names
from features.player_form import add_player_rolling_features, aggregate_player_gameweeks
from features.team_strength import add_team_rolling_ratings, unique_team_matches
from modelling.predict import ALL_MODELS, ModelSpec, predict_frame
from modelling.scoring import load_scoring_rules


IDENTITY_COLS = [
    "element",
    "name",
    "position",
    "team",
    "opponent_team",
    "opponent_name",
    "was_home",
    "fixture",
    "GW",
    "season",
    "kickoff_time",
]


@dataclass
class BacktestResult:
    season: str
    model_key: str
    metrics: dict
    predictions: pd.DataFrame


def align_history(df: pd.DataFrame, source_season: str, target_code_to_element: dict[int, int]) -> pd.DataFrame:
    """Rewrite season-specific element ids onto the target season using stable FPL codes."""
    aligned = remap_elements_to_codes(df, source_season)
    aligned = aligned[aligned["code"].notna()].copy()
    aligned["element"] = aligned["code"].map(target_code_to_element)
    return aligned[aligned["element"].notna()].copy()


def add_timeline(df: pd.DataFrame, season_order: dict[str, int]) -> pd.DataFrame:
    out = df.copy()
    out["timeline"] = out["season"].map(season_order).fillna(0).astype(int) * 100 + out["GW"].astype(int)
    return out


def actuals_by_player_gw(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["element", "GW"], as_index=False)
        .agg(actual_points=("total_points", "sum"), actual_minutes=("minutes", "sum"), n_fixtures=("element", "size"))
    )


def run_model_backtest(
    season: str,
    spec: ModelSpec,
    current: pd.DataFrame,
    prior: pd.DataFrame | None,
    teams: pd.DataFrame | None,
    min_minutes: int = 1,
) -> BacktestResult:
    season_order = {s: i for i, s in enumerate(sorted({*(prior["season"].unique() if prior is not None and not prior.empty else []), season}))}
    current = add_timeline(current, season_order)
    history_pool = current.copy()
    if prior is not None and not prior.empty:
        history_pool = pd.concat([add_timeline(prior, season_order), current], ignore_index=True)

    actuals = actuals_by_player_gw(current)
    rules = load_scoring_rules()
    print(f"precomputing rolling features for {spec.key} rows={len(history_pool)}", flush=True)
    promoted = set()
    try:
        from modelling.scoring import load_season_config

        promoted = set(load_season_config().get("seasons", {}).get(season, {}).get("promoted", []))
    except Exception:
        promoted = set()
    pre_pgw = add_player_rolling_features(aggregate_player_gameweeks(history_pool), exclude_current_row=False)
    pre_teams = add_team_rolling_ratings(unique_team_matches(history_pool), promoted_teams=promoted)
    frames = []
    gameweeks = sorted(int(g) for g in current["GW"].dropna().unique())
    cutoff = season_order[season] * 100
    for gw in gameweeks:
        upcoming = current.loc[current["GW"] == gw, [c for c in IDENTITY_COLS if c in current.columns]].copy()
        if upcoming.empty:
            continue
        history = history_pool[history_pool["timeline"] < cutoff + gw]
        if gw == gameweeks[0] or gw % 5 == 0:
            print(f"backtest {spec.key} GW{gw}/{gameweeks[-1]} history_rows={len(history)}", flush=True)
        features = build_upcoming_features(
            history=history,
            upcoming=upcoming,
            teams=teams,
            season=season,
            use_xg_ratings=spec.use_xg,
            include_h2h=spec.include_h2h,
            precomputed_pgw=pre_pgw,
            precomputed_team_ratings=pre_teams,
            timeline_cutoff=cutoff + gw,
        )
        preds = predict_frame(features, spec, rules)
        if preds.empty:
            continue
        merged = preds.merge(actuals[actuals["GW"] == gw], on=["element", "GW"], how="left")
        merged["actual_points"] = merged["actual_points"].fillna(0)
        frames.append(merged)

    predictions = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    scored = predictions[predictions["actual_minutes"].fillna(0) >= min_minutes] if not predictions.empty else predictions
    if scored.empty:
        scored = predictions
    metrics = summarise_model(scored) if not scored.empty else {"n": 0}
    metrics["model"] = spec.name
    metrics["season"] = season
    metrics["gameweeks"] = len(gameweeks)
    return BacktestResult(season=season, model_key=spec.key, metrics=metrics, predictions=predictions)


def run_all_models(
    season: str | None = None,
    include_prior: bool = True,
    models: list[ModelSpec] | None = None,
) -> list[BacktestResult]:
    settings = get_settings()
    season = season or settings.historical_season
    teams = load_teams(season, download=True)
    current = resolve_opponent_names(load_merged_gameweeks(season, download=True), teams)
    target_ids = load_player_codes(season, download=True)
    code_to_element = dict(zip(target_ids["code"].astype(int), target_ids["element"].astype(int)))
    prior = None
    if include_prior:
        try:
            prior_teams = load_teams(settings.prior_season, download=True)
            raw_prior = resolve_opponent_names(load_merged_gameweeks(settings.prior_season, download=True), prior_teams)
            prior = align_history(raw_prior, settings.prior_season, code_to_element)
        except Exception:
            prior = None
    results = []
    for spec in models or ALL_MODELS:
        results.append(run_model_backtest(season, spec, current, prior, teams))
    return results


def write_report(results: list[BacktestResult], path: Path | None = None) -> Path:
    settings = get_settings()
    path = path or (settings.report_dir / f"backtest_{results[0].season}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {results[0].season} BACKTEST",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Model version: {results[0].predictions['model_version'].iloc[0] if not results[0].predictions.empty else 'n/a'}",
        f"Feature version: {results[0].predictions['feature_version'].iloc[0] if not results[0].predictions.empty else 'n/a'}",
        "",
        "Walk-forward protocol: for Gameweek N, features use only rows with timeline < N.",
        "Double Gameweeks are summed. Blank Gameweeks contribute 0 fixtures / 0 xPts.",
        "",
        "| Model | n | MAE | RMSE | Corr | Spearman | Top 10 avg actual | Captain avg actual |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        m = result.metrics
        lines.append(
            "| {model} | {n} | {mae} | {rmse} | {corr} | {spearman} | {top10} | {cap} |".format(
                model=m.get("model"),
                n=m.get("n"),
                mae=_fmt(m.get("mae")),
                rmse=_fmt(m.get("rmse")),
                corr=_fmt(m.get("corr")),
                spearman=_fmt(m.get("spearman")),
                top10=_fmt(m.get("top10_avg_actual")),
                cap=_fmt(m.get("captain_avg_actual")),
            )
        )
    lines.extend(["", "## Notes", ""])
    strongest = min(results, key=lambda r: r.metrics.get("mae") if r.metrics.get("mae") is not None else 9e9)
    lines.append(f"Lowest MAE on this run: **{strongest.metrics.get('model')}**.")
    lines.append("This is an initial transparent statistical baseline, not a claim of production superiority.")
    lines.append("H2H is included only in Model D and is shrinkage-weighted so it cannot dominate.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    comparison = path.with_name(path.stem + "_comparison.csv")
    pd.DataFrame([r.metrics for r in results]).to_csv(comparison, index=False)
    return path


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)
