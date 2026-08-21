from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_secret_key: str = "change-me"
    admin_api_token: str = "change-me"

    database_url: str = "sqlite:///./fpl_local.db"

    fpl_user_agent: str = "FPLPredictor/0.1"
    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    historical_repo_base: str = (
        "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
    )

    data_cache_dir: Path = ROOT / "data" / "cache"
    snapshot_dir: Path = ROOT / "data" / "snapshots"
    report_dir: Path = ROOT / "reports" / "generated"
    config_dir: Path = ROOT / "config"
    log_level: str = "INFO"

    timezone: str = "Europe/London"
    daily_refresh_hour: int = 9
    daily_refresh_minute: int = 0

    model_version: str = "0.1.1"
    feature_version: str = "0.1.0"
    current_season: str = "2026-27"
    historical_season: str = "2025-26"
    prior_season: str = "2024-25"

    differential_ownership_max: float = 10.0
    ultra_differential_ownership_max: float = 5.0
    hit_min_net_xpts: float = 1.5


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.snapshot_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    return settings
