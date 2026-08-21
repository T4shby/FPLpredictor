from data.clients.fpl_client import detect_schema_changes, map_player, map_position
from data.validation.validators import validate_bootstrap, validate_fixtures


def test_unknown_element_type_is_rejected():
    try:
        map_position(9)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_map_player_uses_adapter_not_raw_field_names_in_output():
    raw = {
        "id": 1,
        "web_name": "Test",
        "element_type": 4,
        "team": 1,
        "now_cost": 100,
        "status": "a",
        "minutes": 10,
        "total_points": 4,
        "first_name": "A",
        "second_name": "B",
        "selected_by_percent": "12.3",
    }
    mapped = map_player(raw)
    assert mapped["fpl_element_id"] == 1
    assert mapped["position"] == "FWD"
    assert "element_type" not in mapped


def test_bootstrap_validation_catches_missing_keys():
    result = validate_bootstrap({"teams": []})
    assert result.ok is False
    assert any("missing key" in err for err in result.errors)


def test_schema_change_detector():
    warnings = detect_schema_changes({"a": 1}, {"a", "b"})
    assert warnings == ["missing key: b"]


def test_duplicate_fixture_ids_fail_validation():
    fixtures = [
        {"id": 1, "event": 1, "team_h": 1, "team_a": 2, "kickoff_time": "x", "finished": False},
        {"id": 1, "event": 1, "team_h": 3, "team_a": 4, "kickoff_time": "x", "finished": False},
    ]
    result = validate_fixtures(fixtures, team_ids={1, 2, 3, 4})
    assert result.ok is False
