from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from backend.app.core.settings import ROOT, get_settings


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_scoring_rules(path: Path | None = None) -> dict[str, Any]:
    settings = get_settings()
    target = path or (settings.config_dir / "scoring_rules.yaml")
    return load_yaml(target)


def load_season_config(path: Path | None = None) -> dict[str, Any]:
    settings = get_settings()
    target = path or (settings.config_dir / "seasons.yaml")
    return load_yaml(target)


def position_goal_points(rules: dict[str, Any], position: str) -> int:
    return int(rules["goals_scored"][position])


def position_cs_points(rules: dict[str, Any], position: str) -> int:
    return int(rules["clean_sheets"][position])


def position_gc_points(rules: dict[str, Any], position: str) -> int:
    return int(rules["goals_conceded"][position])


def position_defcon_points(rules: dict[str, Any], position: str) -> int:
    return int(rules["defensive_contribution"][position])


def appearance_points(rules: dict[str, Any], expected_minutes: float, p_start: float, p_60: float) -> float:
    """Expected appearance points from minutes probabilities.

    short_play is 1 if the player appears. long_play is 2 if they reach 60 minutes.
    A player who reaches 60 minutes receives long_play, not short+long.
    """
    p_appear = min(1.0, max(p_start, min(1.0, expected_minutes / 90.0)))
    p_long = min(1.0, p_60)
    p_short_only = max(0.0, p_appear - p_long)
    return (
        p_short_only * float(rules["appearance"]["short_play"])
        + p_long * float(rules["appearance"]["long_play"])
    )


def save_points(rules: dict[str, Any], expected_saves: float) -> float:
    unit = float(rules["saves"]["saves_per_unit"])
    pts = float(rules["saves"]["points_per_unit"])
    if unit <= 0:
        return 0.0
    return expected_saves / unit * pts


def gc_deduction(rules: dict[str, Any], position: str, expected_goals_conceded: float, p_60: float) -> float:
    per = float(rules["goals_conceded"]["goals_per_deduction"])
    rate = position_gc_points(rules, position)
    if per <= 0 or rate == 0:
        return 0.0
    return p_60 * expected_goals_conceded / per * rate


CONFIG_ROOT = ROOT / "config"
