from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.db.models import (
    Fixture,
    Gameweek,
    Player,
    PlayerSnapshot,
    RawApiSnapshot,
    ScoringRuleset,
    SystemJob,
    Team,
)
from data.clients.fpl_client import FplClient, map_fixture, map_gameweek, map_player, map_team
from data.ingestion.snapshots import write_json_snapshot
from data.validation.validators import validate_bootstrap, validate_fixtures
from modelling.scoring import load_season_config


def promoted_names(season: str) -> set[str]:
    config = load_season_config()
    names = config.get("seasons", {}).get(season, {}).get("promoted", [])
    return set(names)


def import_live_snapshot(session: Session, client: FplClient | None = None) -> dict:
    settings = get_settings()
    client = client or FplClient()
    captured_at = datetime.now(timezone.utc)
    bootstrap = client.bootstrap_static()
    fixtures_raw = client.fixtures()

    bootstrap_validation = validate_bootstrap(bootstrap)
    team_ids = {team["id"] for team in bootstrap.get("teams", [])}
    fixture_validation = validate_fixtures(fixtures_raw, team_ids=team_ids)
    ok = bootstrap_validation.ok and fixture_validation.ok

    bootstrap_meta = write_json_snapshot(bootstrap, "fpl_api", "bootstrap-static", captured_at)
    fixtures_meta = write_json_snapshot(fixtures_raw, "fpl_api", "fixtures", captured_at)

    session.add(
        RawApiSnapshot(
            captured_at=captured_at,
            source="fpl_api",
            endpoint="bootstrap-static",
            season=settings.current_season,
            content_hash=bootstrap_meta["content_hash"],
            storage_path=bootstrap_meta["storage_path"],
            is_valid=bootstrap_validation.ok,
            validation_errors={"errors": bootstrap_validation.errors, "warnings": bootstrap_validation.warnings},
        )
    )
    session.add(
        RawApiSnapshot(
            captured_at=captured_at,
            source="fpl_api",
            endpoint="fixtures",
            season=settings.current_season,
            content_hash=fixtures_meta["content_hash"],
            storage_path=fixtures_meta["storage_path"],
            is_valid=fixture_validation.ok,
            validation_errors={"errors": fixture_validation.errors, "warnings": fixture_validation.warnings},
        )
    )

    if not ok:
        session.commit()
        return {
            "ok": False,
            "errors": bootstrap_validation.errors + fixture_validation.errors,
            "warnings": bootstrap_validation.warnings + fixture_validation.warnings,
        }

    season = settings.current_season
    promoted = promoted_names(season)
    team_rows: dict[int, Team] = {}
    for raw in bootstrap["teams"]:
        mapped = map_team(raw)
        existing = (
            session.query(Team)
            .filter(Team.season == season, Team.fpl_team_id == mapped["fpl_team_id"])
            .one_or_none()
        )
        if existing is None:
            existing = Team(season=season, fpl_team_id=mapped["fpl_team_id"])
            session.add(existing)
        existing.code = mapped["code"]
        existing.name = mapped["name"]
        existing.short_name = mapped["short_name"]
        existing.is_promoted = mapped["name"] in promoted
        team_rows[mapped["fpl_team_id"]] = existing
    session.flush()

    for raw in bootstrap["elements"]:
        mapped = map_player(raw)
        existing = (
            session.query(Player)
            .filter(Player.season == season, Player.fpl_element_id == mapped["fpl_element_id"])
            .one_or_none()
        )
        if existing is None:
            existing = Player(season=season, fpl_element_id=mapped["fpl_element_id"])
            session.add(existing)
        existing.code = mapped["code"]
        existing.first_name = mapped["first_name"]
        existing.second_name = mapped["second_name"]
        existing.web_name = mapped["web_name"]
        existing.position = mapped["position"]
        existing.team_id = team_rows[mapped["fpl_team_id"]].id
        session.add(
            PlayerSnapshot(
                captured_at=captured_at,
                season=season,
                fpl_element_id=mapped["fpl_element_id"],
                web_name=mapped["web_name"],
                position=mapped["position"],
                fpl_team_id=mapped["fpl_team_id"],
                now_cost=mapped["now_cost"],
                selected_by_percent=mapped["selected_by_percent"],
                status=mapped["status"],
                chance_of_playing_next_round=mapped["chance_of_playing_next_round"],
                news=mapped["news"],
                minutes=mapped["minutes"],
                total_points=mapped["total_points"],
                expected_goals=mapped["expected_goals"],
                expected_assists=mapped["expected_assists"],
                penalties_order=mapped["penalties_order"],
                corners_order=mapped["corners_order"],
                raw=None,
            )
        )

    for raw in bootstrap["events"]:
        mapped = map_gameweek(raw)
        existing = (
            session.query(Gameweek)
            .filter(Gameweek.season == season, Gameweek.event_id == mapped["event_id"])
            .one_or_none()
        )
        if existing is None:
            existing = Gameweek(season=season, event_id=mapped["event_id"], name=mapped["name"])
            session.add(existing)
        existing.name = mapped["name"]
        existing.deadline_time = _parse_dt(mapped["deadline_time"])
        existing.is_current = mapped["is_current"]
        existing.is_next = mapped["is_next"]
        existing.finished = mapped["finished"]

    for raw in fixtures_raw:
        mapped = map_fixture(raw)
        existing = (
            session.query(Fixture)
            .filter(Fixture.season == season, Fixture.fpl_fixture_id == mapped["fpl_fixture_id"])
            .one_or_none()
        )
        if existing is None:
            existing = Fixture(season=season, fpl_fixture_id=mapped["fpl_fixture_id"])
            session.add(existing)
        existing.event_id = mapped["event_id"]
        existing.kickoff_time = _parse_dt(mapped["kickoff_time"])
        existing.home_team_id = team_rows[mapped["home_fpl_team_id"]].id
        existing.away_team_id = team_rows[mapped["away_fpl_team_id"]].id
        existing.home_score = mapped["home_score"]
        existing.away_score = mapped["away_score"]
        existing.finished = mapped["finished"]
        existing.minutes = mapped["minutes"]
        existing.postponed = mapped["postponed"]

    scoring = bootstrap.get("game_config", {}).get("scoring")
    if scoring:
        session.add(
            ScoringRuleset(
                season=season,
                captured_at=captured_at,
                rules=scoring,
                is_active=True,
            )
        )

    session.commit()
    return {
        "ok": True,
        "captured_at": captured_at.isoformat(),
        "players": len(bootstrap["elements"]),
        "teams": len(bootstrap["teams"]),
        "fixtures": len(fixtures_raw),
        "warnings": bootstrap_validation.warnings + fixture_validation.warnings,
    }


def record_job(session: Session, job_name: str, status: str, message: str = "", attempt: int = 1, details: dict | None = None) -> None:
    now = datetime.now(timezone.utc)
    session.add(
        SystemJob(
            job_name=job_name,
            started_at=now,
            finished_at=now,
            status=status,
            attempt=attempt,
            message=message,
            details=details,
        )
    )
    session.commit()


def _parse_dt(value: str | None):
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    return datetime.fromisoformat(text)
