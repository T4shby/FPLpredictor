from __future__ import annotations

from typing import Any

import httpx

from backend.app.core.settings import get_settings


POSITION_MAP = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

BOOTSTRAP_REQUIRED_KEYS = {
    "events",
    "teams",
    "elements",
    "element_types",
    "game_config",
}

ELEMENT_REQUIRED_FIELDS = {
    "id",
    "web_name",
    "element_type",
    "team",
    "now_cost",
    "status",
    "minutes",
    "total_points",
}

FIXTURE_REQUIRED_FIELDS = {
    "id",
    "event",
    "team_h",
    "team_a",
    "kickoff_time",
    "finished",
}


class FplApiError(RuntimeError):
    pass


class FplClient:
    """Thin HTTP adapter around unofficial FPL JSON endpoints.

    Upstream field names stay here. Application code should consume the
    normalised dictionaries returned by the mapping helpers.
    """

    def __init__(self, base_url: str | None = None, user_agent: str | None = None, timeout: float = 60.0):
        settings = get_settings()
        self.base_url = (base_url or settings.fpl_base_url).rstrip("/")
        self.user_agent = user_agent or settings.fpl_user_agent
        self.timeout = timeout

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        try:
            with httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise FplApiError(f"FPL request failed for {url}: {exc}") from exc

    def bootstrap_static(self) -> dict:
        return self._get("bootstrap-static/")

    def fixtures(self) -> list[dict]:
        payload = self._get("fixtures/")
        if not isinstance(payload, list):
            raise FplApiError("fixtures endpoint did not return a list")
        return payload

    def event_live(self, event_id: int) -> dict:
        return self._get(f"event/{event_id}/live/")

    def element_summary(self, element_id: int) -> dict:
        return self._get(f"element-summary/{element_id}/")

    def entry(self, entry_id: int) -> dict:
        return self._get(f"entry/{entry_id}/")

    def entry_picks(self, entry_id: int, event_id: int) -> dict:
        return self._get(f"entry/{entry_id}/event/{event_id}/picks/")


def detect_schema_changes(payload: dict, required_keys: set[str]) -> list[str]:
    missing = sorted(required_keys - set(payload))
    return [f"missing key: {key}" for key in missing]


def map_position(element_type: int) -> str:
    if element_type not in POSITION_MAP:
        raise ValueError(f"Unknown element_type {element_type}")
    return POSITION_MAP[element_type]


def map_team(raw: dict) -> dict:
    return {
        "fpl_team_id": raw["id"],
        "code": raw.get("code"),
        "name": raw["name"],
        "short_name": raw["short_name"],
        "strength_overall_home": raw.get("strength_overall_home"),
        "strength_overall_away": raw.get("strength_overall_away"),
        "strength_attack_home": raw.get("strength_attack_home"),
        "strength_attack_away": raw.get("strength_attack_away"),
        "strength_defence_home": raw.get("strength_defence_home"),
        "strength_defence_away": raw.get("strength_defence_away"),
    }


def map_player(raw: dict) -> dict:
    return {
        "fpl_element_id": raw["id"],
        "code": raw.get("code"),
        "first_name": raw.get("first_name") or "",
        "second_name": raw.get("second_name") or "",
        "web_name": raw["web_name"],
        "position": map_position(int(raw["element_type"])),
        "fpl_team_id": raw["team"],
        "now_cost": raw["now_cost"],
        "selected_by_percent": float(raw.get("selected_by_percent") or 0),
        "status": raw.get("status") or "a",
        "chance_of_playing_this_round": raw.get("chance_of_playing_this_round"),
        "chance_of_playing_next_round": raw.get("chance_of_playing_next_round"),
        "news": raw.get("news") or "",
        "minutes": int(raw.get("minutes") or 0),
        "starts": int(raw.get("starts") or 0),
        "total_points": int(raw.get("total_points") or 0),
        "goals_scored": int(raw.get("goals_scored") or 0),
        "assists": int(raw.get("assists") or 0),
        "clean_sheets": int(raw.get("clean_sheets") or 0),
        "goals_conceded": int(raw.get("goals_conceded") or 0),
        "saves": int(raw.get("saves") or 0),
        "bonus": int(raw.get("bonus") or 0),
        "bps": int(raw.get("bps") or 0),
        "expected_goals": float(raw.get("expected_goals") or 0),
        "expected_assists": float(raw.get("expected_assists") or 0),
        "expected_goal_involvements": float(raw.get("expected_goal_involvements") or 0),
        "expected_goals_conceded": float(raw.get("expected_goals_conceded") or 0),
        "defensive_contribution": int(raw.get("defensive_contribution") or 0),
        "clearances_blocks_interceptions": int(raw.get("clearances_blocks_interceptions") or 0),
        "recoveries": int(raw.get("recoveries") or 0),
        "tackles": int(raw.get("tackles") or 0),
        "penalties_order": raw.get("penalties_order"),
        "corners_order": raw.get("corners_and_indirect_freekicks_order"),
        "direct_freekicks_order": raw.get("direct_freekicks_order"),
        "expected_goals_per_90": float(raw.get("expected_goals_per_90") or 0),
        "expected_assists_per_90": float(raw.get("expected_assists_per_90") or 0),
        "defensive_contribution_per_90": float(raw.get("defensive_contribution_per_90") or 0),
        "raw": raw,
    }


def map_fixture(raw: dict) -> dict:
    return {
        "fpl_fixture_id": raw["id"],
        "event_id": raw.get("event"),
        "kickoff_time": raw.get("kickoff_time"),
        "home_fpl_team_id": raw["team_h"],
        "away_fpl_team_id": raw["team_a"],
        "home_score": raw.get("team_h_score"),
        "away_score": raw.get("team_a_score"),
        "finished": bool(raw.get("finished")),
        "started": bool(raw.get("started")),
        "minutes": int(raw.get("minutes") or 0),
        "postponed": raw.get("event") is None and not raw.get("finished"),
        "home_difficulty": raw.get("team_h_difficulty"),
        "away_difficulty": raw.get("team_a_difficulty"),
        "stats": raw.get("stats") or [],
        "raw": raw,
    }


def map_gameweek(raw: dict) -> dict:
    return {
        "event_id": raw["id"],
        "name": raw["name"],
        "deadline_time": raw.get("deadline_time"),
        "is_previous": bool(raw.get("is_previous")),
        "is_current": bool(raw.get("is_current")),
        "is_next": bool(raw.get("is_next")),
        "finished": bool(raw.get("finished")),
        "average_entry_score": raw.get("average_entry_score"),
    }
