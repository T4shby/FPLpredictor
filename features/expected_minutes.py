from __future__ import annotations

import numpy as np
import pandas as pd


POSITION_MINUTE_PRIOR = {"GKP": 70.0, "DEF": 60.0, "MID": 55.0, "FWD": 50.0}


def expected_minutes_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorised expected minutes for a feature frame."""
    n_fx = np.asarray(pd.to_numeric(df.get("n_fixtures_upcoming", 1), errors="coerce").fillna(1), dtype=float)
    n_fx = np.clip(n_fx, 1, None)
    n_matches = np.asarray(pd.to_numeric(df.get("minutes_prev_matches", 0), errors="coerce").fillna(0), dtype=float)
    last3 = np.asarray(pd.to_numeric(df.get("minutes_l3", 0), errors="coerce").fillna(0), dtype=float)
    last5 = np.asarray(pd.to_numeric(df.get("minutes_l5", 0), errors="coerce").fillna(0), dtype=float)
    last8 = np.asarray(pd.to_numeric(df.get("minutes_l8", 0), errors="coerce").fillna(0), dtype=float)
    last_minutes = np.asarray(pd.to_numeric(df.get("minutes_prev", 0), errors="coerce").fillna(0), dtype=float)
    starts3 = np.asarray(pd.to_numeric(df.get("starts_l3", 0), errors="coerce").fillna(0), dtype=float)
    n3 = np.clip(np.minimum(3, n_matches), 1, None)
    n5 = np.clip(np.minimum(5, n_matches), 1, None)
    n8 = np.clip(np.minimum(8, n_matches), 1, None)
    if "position" in df.columns:
        prior = df["position"].map(POSITION_MINUTE_PRIOR).fillna(55.0).to_numpy(dtype=float)
    else:
        prior = np.full(len(df), 55.0)
    avg3 = last3 / n3
    avg5 = last5 / n5
    avg8 = last8 / n8
    exp_gw = 0.5 * avg3 + 0.3 * avg5 + 0.2 * avg8
    exp_gw = np.where(n_matches <= 0, prior * 0.6, exp_gw)
    p_start = np.where(n_matches <= 0, 0.45, starts3 / n3)
    p_60 = np.where(n_matches <= 0, 0.35, np.minimum(1.0, avg3 / 90.0))
    injured = (last_minutes == 0) & (avg5 >= 45) & (n_matches > 0)
    exp_gw = np.where(injured, exp_gw * 0.55, exp_gw)
    p_start = np.where(injured, p_start * 0.6, p_start)
    p_60 = np.where(injured, p_60 * 0.5, p_60)
    per_fixture = exp_gw / n_fx
    per_fixture = np.where(n_fx >= 2, per_fixture * 0.85, per_fixture)
    p_start = np.where(n_fx >= 2, p_start * 0.85, p_start)
    p_60 = np.where(n_fx >= 2, p_60 * 0.8, p_60)
    out = df.copy()
    out["expected_minutes"] = np.clip(per_fixture, 0, 90)
    out["start_probability"] = np.clip(p_start, 0, 0.99)
    out["p_60"] = np.clip(np.minimum(p_60, p_start), 0, 0.99)
    return out


def expected_minutes_from_rolling(row: pd.Series, n_fixtures: int = 1) -> dict[str, float]:
    frame = expected_minutes_frame(pd.DataFrame([row]).assign(n_fixtures_upcoming=n_fixtures))
    rec = frame.iloc[0]
    return {
        "expected_minutes": float(rec["expected_minutes"]),
        "start_probability": float(rec["start_probability"]),
        "p_60": float(rec["p_60"]),
    }
