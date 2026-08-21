from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from data.clients.fpl_client import (
    BOOTSTRAP_REQUIRED_KEYS,
    ELEMENT_REQUIRED_FIELDS,
    FIXTURE_REQUIRED_FIELDS,
    detect_schema_changes,
)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.ok:
            raise ValueError("; ".join(self.errors))


def validate_bootstrap(payload: dict) -> ValidationResult:
    errors = detect_schema_changes(payload, BOOTSTRAP_REQUIRED_KEYS)
    warnings: list[str] = []
    teams = payload.get("teams") or []
    elements = payload.get("elements") or []
    events = payload.get("events") or []
    if not 18 <= len(teams) <= 22:
        errors.append(f"unexpected team count: {len(teams)}")
    if not 400 <= len(elements) <= 900:
        errors.append(f"unexpected player count: {len(elements)}")
    if len(events) != 38:
        warnings.append(f"event count is {len(events)}, expected 38")
    if elements:
        missing = ELEMENT_REQUIRED_FIELDS - set(elements[0])
        if missing:
            errors.append(f"element missing fields: {sorted(missing)}")
    team_ids = {team["id"] for team in teams if "id" in team}
    unresolved = [el["id"] for el in elements if el.get("team") not in team_ids]
    if unresolved:
        errors.append(f"{len(unresolved)} players reference unknown teams")
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def validate_fixtures(fixtures: list[dict], team_ids: set[int] | None = None) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if not 300 <= len(fixtures) <= 500:
        warnings.append(f"fixture count is {len(fixtures)}")
    seen: set[int] = set()
    for fixture in fixtures:
        missing = FIXTURE_REQUIRED_FIELDS - set(fixture)
        if missing:
            errors.append(f"fixture missing fields: {sorted(missing)}")
            break
        fid = fixture["id"]
        if fid in seen:
            errors.append(f"duplicate fixture id {fid}")
        seen.add(fid)
        if team_ids is not None:
            if fixture.get("team_h") not in team_ids or fixture.get("team_a") not in team_ids:
                errors.append(f"fixture {fid} has unresolved team ids")
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def validate_player_gameweeks(df: pd.DataFrame) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    required = {"element", "GW", "minutes", "total_points", "position", "team"}
    missing = required - set(df.columns)
    if missing:
        errors.append(f"player-gameweek missing columns: {sorted(missing)}")
        return ValidationResult(ok=False, errors=errors)
    if df.empty:
        errors.append("player-gameweek frame is empty")
    if (df["minutes"] < 0).any() or (df["minutes"] > 180).any():
        errors.append("impossible minutes values present")
    if df["GW"].min() < 1 or df["GW"].max() > 38:
        warnings.append(f"GW range {df['GW'].min()}-{df['GW'].max()} is outside 1-38")
    dup_cols = ["element", "GW"]
    if "fixture" in df.columns:
        dup_cols.append("fixture")
    if df.duplicated(dup_cols).any():
        warnings.append("duplicate player/gameweek/fixture rows were present before load")
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def summarise_frame(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "null_counts": {col: int(df[col].isna().sum()) for col in df.columns},
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }
