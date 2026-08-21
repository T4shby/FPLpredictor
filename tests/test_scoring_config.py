from modelling.scoring import load_scoring_rules, load_season_config


def test_scoring_rules_match_verified_2026_27_fpl_config():
    rules = load_scoring_rules()
    assert rules["goals_scored"]["FWD"] == 4
    assert rules["goals_scored"]["MID"] == 5
    assert rules["goals_scored"]["DEF"] == 6
    assert rules["goals_scored"]["GKP"] == 10
    assert rules["clean_sheets"]["GKP"] == 4
    assert rules["defensive_contribution"]["DEF"] == 2
    assert rules["saves"]["saves_per_unit"] == 3


def test_promoted_teams_are_named_not_id_hardcoded():
    seasons = load_season_config()["seasons"]
    assert "Coventry City" in seasons["2026-27"]["promoted"]
    assert "Burnley" in seasons["2025-26"]["promoted"]
