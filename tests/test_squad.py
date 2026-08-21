from __future__ import annotations

from collections import Counter

from optimisation.squad import apply_autosubs, score_squad, select_squad, squad_rules


def _pool(extra=None) -> list[dict]:
    rows = []
    eid = 1
    clubs = [f"T{i}" for i in range(8)]
    for pos, n, base in (("GKP", 6, 40), ("DEF", 12, 45), ("MID", 12, 50), ("FWD", 8, 70)):
        for i in range(n):
            rows.append(
                {
                    "element": eid,
                    "name": f"{pos}{i}",
                    "team": clubs[i % 8],
                    "position": pos,
                    "now_cost": base + (i % 4) * 5,
                    "xpts_gw": 6.0 - i * 0.12,
                    "expected_minutes": 90,
                }
            )
            eid += 1
    if extra:
        rows.extend(extra)
    return rows


def test_select_squad_is_legal_fpl_team():
    rules = squad_rules()
    squad = select_squad(_pool())
    players = squad["players"]
    assert len(players) == 15
    assert squad["cost_tenths"] <= rules["budget"]
    assert squad["bank_tenths"] == rules["budget"] - squad["cost_tenths"]
    pos = Counter(p["position"] for p in players)
    assert pos == {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
    assert max(Counter(p["team"] for p in players).values()) <= 3
    starters = [p for p in players if p["starter"]]
    assert len(starters) == 11
    assert sum(1 for p in starters if p["position"] == "GKP") == 1
    cap_ids = {p["element"] for p in starters}
    assert squad["captain_element"] in cap_ids
    assert squad["vice_element"] in cap_ids


def test_three_per_club_even_if_one_team_has_higher_xpts():
    extra = []
    for i in range(6):
        extra.append(
            {
                "element": 900 + i,
                "name": f"Star{i}",
                "team": "T0",
                "position": "MID",
                "now_cost": 80,
                "xpts_gw": 20.0,
                "expected_minutes": 90,
            }
        )
    squad = select_squad(_pool(extra))
    assert Counter(p["team"] for p in squad["players"])["T0"] <= 3


def test_captain_blank_uses_vice_double():
    players = [
        {"element": 1, "position": "GKP", "starter": True, "bench_order": 0},
        {"element": 2, "position": "DEF", "starter": True, "bench_order": 0},
        {"element": 3, "position": "DEF", "starter": True, "bench_order": 0},
        {"element": 4, "position": "DEF", "starter": True, "bench_order": 0},
        {"element": 5, "position": "MID", "starter": True, "bench_order": 0},
        {"element": 6, "position": "MID", "starter": True, "bench_order": 0},
        {"element": 7, "position": "MID", "starter": True, "bench_order": 0},
        {"element": 8, "position": "MID", "starter": True, "bench_order": 0},
        {"element": 9, "position": "FWD", "starter": True, "bench_order": 0},
        {"element": 10, "position": "FWD", "starter": True, "bench_order": 0},
        {"element": 11, "position": "FWD", "starter": True, "bench_order": 0},
        {"element": 12, "position": "DEF", "starter": False, "bench_order": 1},
        {"element": 13, "position": "MID", "starter": False, "bench_order": 2},
        {"element": 14, "position": "FWD", "starter": False, "bench_order": 3},
        {"element": 15, "position": "GKP", "starter": False, "bench_order": 4},
    ]
    live = {i: {"minutes": 90, "points": 2} for i in range(1, 16)}
    live[1] = {"minutes": 0, "points": 0}  # captain GK blanked
    live[15] = {"minutes": 90, "points": 4}
    playing = apply_autosubs(players, live, event_finished=True)
    assert 15 in {p["element"] for p in playing}
    assert 1 not in {p["element"] for p in playing}
    scored = score_squad(players, captain_element=9, vice_element=10, live=live, event_finished=True)
    # 10 field players at 2, GK sub at 4, captain 9 played so doubled +2 extra
    assert scored["doubled"] == 9
    assert scored["actual_points"] == 2 * 10 + 4 + 2


def test_no_autosub_until_gameweek_finished():
    squad = select_squad(_pool())
    live = {p["element"]: {"minutes": 0, "points": 0} for p in squad["players"]}
    playing = apply_autosubs(squad["players"], live, event_finished=False)
    assert [p["element"] for p in playing] == [p["element"] for p in squad["players"] if p["starter"]]
