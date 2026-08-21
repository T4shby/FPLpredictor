from __future__ import annotations

import numpy as np
import pandas as pd


def regression_metrics(predicted: pd.Series, actual: pd.Series) -> dict[str, float]:
    aligned = pd.concat([predicted.rename("yhat"), actual.rename("y")], axis=1).dropna()
    if aligned.empty:
        return {"n": 0, "mae": None, "rmse": None, "corr": None}
    err = aligned["yhat"] - aligned["y"]
    corr = float(aligned["yhat"].corr(aligned["y"])) if len(aligned) > 2 else None
    return {
        "n": int(len(aligned)),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(np.square(err)))),
        "corr": corr,
    }


def ranking_metrics(frame: pd.DataFrame, predicted_col: str = "xpts", actual_col: str = "actual_points") -> dict:
    if frame.empty:
        return {}
    per_gw = []
    for _, group in frame.groupby("GW"):
        ranked = group.sort_values(predicted_col, ascending=False)
        row = {
            "top5_avg_actual": float(ranked.head(5)[actual_col].mean()) if len(ranked) else None,
            "top10_avg_actual": float(ranked.head(10)[actual_col].mean()) if len(ranked) else None,
            "top20_avg_actual": float(ranked.head(20)[actual_col].mean()) if len(ranked) else None,
            "top50_avg_actual": float(ranked.head(50)[actual_col].mean()) if len(ranked) else None,
            "captain_avg_actual": float(ranked.iloc[0][actual_col]) if len(ranked) else None,
        }
        per_gw.append(row)
    summary = pd.DataFrame(per_gw).mean(numeric_only=True).to_dict()
    if len(frame) > 5:
        summary["spearman"] = float(frame[predicted_col].corr(frame[actual_col], method="spearman"))
    else:
        summary["spearman"] = None
    return summary


def naive_benchmarks(frame: pd.DataFrame) -> dict:
    """Random and form-naive baselines using actual points already in the frame."""
    if frame.empty:
        return {}
    rng = np.random.default_rng(42)
    random_avg = float(frame["actual_points"].sample(n=min(10, len(frame)), random_state=42).mean()) if len(frame) else None
    if "minutes_l5" in frame.columns:
        form = frame.sort_values("total_points_l5", ascending=False) if "total_points_l5" in frame.columns else frame
        form_top10 = float(form.head(10)["actual_points"].mean())
    else:
        form_top10 = None
    return {"random_top10_avg_actual": random_avg, "form_top10_avg_actual": form_top10}


def summarise_model(predictions: pd.DataFrame) -> dict:
    metrics = regression_metrics(predictions["xpts"], predictions["actual_points"])
    metrics.update(ranking_metrics(predictions))
    return metrics
