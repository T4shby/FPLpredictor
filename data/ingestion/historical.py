from __future__ import annotations

from pathlib import Path

import httpx
import pandas as pd

from backend.app.core.settings import get_settings
from data.validation.validators import validate_player_gameweeks

POSITION_ALIASES = {
    "GK": "GKP",
    "GKP": "GKP",
    "DEF": "DEF",
    "MID": "MID",
    "FWD": "FWD",
}

RENAME_MAP = {
    "xP": "fpl_xp",
    "expected_goals": "expected_goals",
    "expected_assists": "expected_assists",
    "expected_goal_involvements": "expected_goal_involvements",
    "expected_goals_conceded": "expected_goals_conceded",
}


class HistoricalDownloadError(RuntimeError):
    pass


def season_cache_dir(season: str) -> Path:
    settings = get_settings()
    path = settings.data_cache_dir / "historical" / season
    path.mkdir(parents=True, exist_ok=True)
    return path


def historical_url(season: str, relative_path: str) -> str:
    settings = get_settings()
    return f"{settings.historical_repo_base.rstrip('/')}/{season}/{relative_path.lstrip('/')}"


def download_file(url: str, dest: Path, timeout: float = 120.0) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": get_settings().fpl_user_agent, "Accept": "text/csv,*/*"}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code != 200:
            raise HistoricalDownloadError(f"{url} returned {response.status_code}")
        dest.write_bytes(response.content)
    return dest


def ensure_season_files(season: str, force: bool = False) -> dict[str, Path]:
    cache = season_cache_dir(season)
    targets = {
        "merged_gw": ("gws/merged_gw.csv", cache / "merged_gw.csv"),
        "teams": ("teams.csv", cache / "teams.csv"),
        "fixtures": ("fixtures.csv", cache / "fixtures.csv"),
        "cleaned_players": ("cleaned_players.csv", cache / "cleaned_players.csv"),
        "players_raw": ("players_raw.csv", cache / "players_raw.csv"),
        "player_idlist": ("player_idlist.csv", cache / "player_idlist.csv"),
    }
    paths: dict[str, Path] = {}
    for key, (relative, dest) in targets.items():
        if force or not dest.exists():
            download_file(historical_url(season, relative), dest)
        paths[key] = dest
    return paths


def _normalise_position(value: object) -> str:
    text = str(value).strip().upper()
    return POSITION_ALIASES.get(text, text)


def load_merged_gameweeks(season: str, download: bool = True) -> pd.DataFrame:
    if download:
        paths = ensure_season_files(season)
        path = paths["merged_gw"]
    else:
        path = season_cache_dir(season) / "merged_gw.csv"
        if not path.exists():
            raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if "GW" not in df.columns and "round" in df.columns:
        df["GW"] = df["round"]
    if "element" not in df.columns:
        raise ValueError(f"{path} has no element column")
    if "position" in df.columns:
        df["position"] = df["position"].map(_normalise_position)
    numeric_cols = [
        "minutes",
        "starts",
        "total_points",
        "goals_scored",
        "assists",
        "clean_sheets",
        "goals_conceded",
        "own_goals",
        "penalties_saved",
        "penalties_missed",
        "yellow_cards",
        "red_cards",
        "saves",
        "bonus",
        "bps",
        "expected_goals",
        "expected_assists",
        "expected_goal_involvements",
        "expected_goals_conceded",
        "defensive_contribution",
        "clearances_blocks_interceptions",
        "recoveries",
        "tackles",
        "value",
        "selected",
        "was_home",
        "team_a_score",
        "team_h_score",
        "opponent_team",
        "fixture",
        "GW",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    bool_home = df["was_home"] if "was_home" in df.columns else 1
    df["was_home"] = bool_home.fillna(0).astype(int).astype(bool)
    df["season"] = season
    for col in [
        "starts",
        "expected_goals",
        "expected_assists",
        "expected_goal_involvements",
        "expected_goals_conceded",
        "defensive_contribution",
        "clearances_blocks_interceptions",
        "recoveries",
        "tackles",
    ]:
        if col not in df.columns:
            df[col] = 0
    df["GW"] = df["GW"].astype(int)
    df["element"] = df["element"].astype(int)
    subset = ["element", "GW"] + (["fixture"] if "fixture" in df.columns else [])
    df = df.drop_duplicates(subset=subset, keep="first")
    validate_player_gameweeks(df).raise_if_invalid()
    return df


def load_teams(season: str, download: bool = True) -> pd.DataFrame:
    if download:
        path = ensure_season_files(season)["teams"]
    else:
        path = season_cache_dir(season) / "teams.csv"
    df = pd.read_csv(path)
    df["season"] = season
    return df


def load_fixtures(season: str, download: bool = True) -> pd.DataFrame:
    if download:
        path = ensure_season_files(season)["fixtures"]
    else:
        path = season_cache_dir(season) / "fixtures.csv"
    df = pd.read_csv(path)
    df["season"] = season
    if "event" not in df.columns and "GW" in df.columns:
        df["event"] = df["GW"]
    return df


def load_player_codes(season: str, download: bool = True) -> pd.DataFrame:
    """Map season-specific FPL element ids to stable player codes."""
    if download:
        path = ensure_season_files(season)["players_raw"]
    else:
        path = season_cache_dir(season) / "players_raw.csv"
    raw = pd.read_csv(path)
    id_col = "id" if "id" in raw.columns else "element"
    if "code" not in raw.columns:
        raise ValueError(f"{path} has no code column; cannot align players across seasons")
    out = raw[[id_col, "code"]].rename(columns={id_col: "element"})
    out["element"] = out["element"].astype(int)
    out["code"] = out["code"].astype(int)
    return out.drop_duplicates("element")


def remap_elements_to_codes(df: pd.DataFrame, season: str, download: bool = True) -> pd.DataFrame:
    codes = load_player_codes(season, download=download)
    out = df.merge(codes, on="element", how="left")
    return out
