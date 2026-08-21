from __future__ import annotations

from collections import defaultdict

from modelling.scoring import load_scoring_rules

BENCH_WEIGHT = 0.08
FORMATIONS = ((3, 4, 3), (3, 5, 2), (4, 4, 2), (4, 3, 3), (4, 5, 1), (5, 4, 1), (5, 3, 2), (5, 2, 3))


def squad_rules(rules: dict | None = None) -> dict:
    rules = rules or load_scoring_rules()
    spec = rules["squad"]
    positions = spec["positions"]
    return {
        "size": int(spec["size"]),
        "team_limit": int(spec["team_limit"]),
        "budget": int(spec["budget_tenths"]),
        "squad_n": {pos: int(row["squad"]) for pos, row in positions.items()},
        "xi_min": {pos: int(row["min_play"]) for pos, row in positions.items()},
        "xi_max": {pos: int(row["max_play"]) for pos, row in positions.items()},
    }


def frame_to_players(frame) -> list[dict]:
    players = []
    if frame is None or getattr(frame, "empty", True):
        return players
    for _, row in frame.iterrows():
        status = str(row.get("status") or "a")
        if status not in {"a", "d"}:
            continue
        position = str(row.get("position") or "")
        if position not in {"GKP", "DEF", "MID", "FWD"}:
            continue
        cost = int(round(float(row.get("now_cost") or 0)))
        if cost <= 0:
            continue
        players.append(
            {
                "element": int(row["element"]),
                "name": str(row.get("name") or ""),
                "team": str(row.get("team") or ""),
                "position": position,
                "now_cost": cost,
                "xpts_gw": float(row.get("xpts_gw") or 0),
                "expected_minutes": float(row.get("expected_minutes") or 0),
            }
        )
    return players


def trim_pool(players: list[dict]) -> list[dict]:
    """Keep enough premium and cheap options per position for a £100m solve."""
    keep: dict[int, dict] = {}
    by_pos: dict[str, list[dict]] = defaultdict(list)
    for player in players:
        by_pos[player["position"]].append(player)
    caps = {"GKP": 8, "DEF": 20, "MID": 20, "FWD": 12}
    for pos, cap in caps.items():
        ranked = sorted(by_pos[pos], key=lambda p: (-p["xpts_gw"], p["now_cost"]))[:cap]
        cheap = sorted(by_pos[pos], key=lambda p: (p["now_cost"], -p["xpts_gw"]))[:6]
        for player in ranked + cheap:
            keep[player["element"]] = player
    return list(keep.values())


def _counts(players: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for player in players:
        out[str(player[key])] += 1
    return out


def _legal_squad(players: list[dict], rules: dict) -> bool:
    if len(players) != rules["size"]:
        return False
    if sum(p["now_cost"] for p in players) > rules["budget"]:
        return False
    pos = _counts(players, "position")
    if any(pos.get(k, 0) != n for k, n in rules["squad_n"].items()):
        return False
    teams = _counts(players, "team")
    return all(n <= rules["team_limit"] for n in teams.values())


def _xi_score(xi: list[dict], bench: list[dict]) -> float:
    if not xi:
        return -1.0
    pts = sum(p["xpts_gw"] for p in xi)
    captain = max(p["xpts_gw"] for p in xi)
    pts += captain
    pts += BENCH_WEIGHT * sum(p["xpts_gw"] for p in bench)
    return pts


def best_xi(squad: list[dict], rules: dict | None = None) -> dict:
    rules = rules or squad_rules()
    by_pos = defaultdict(list)
    for player in squad:
        by_pos[player["position"]].append(player)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda p: (-p["xpts_gw"], p["now_cost"], p["element"]))
    best = None
    for n_def, n_mid, n_fwd in FORMATIONS:
        if n_def < rules["xi_min"]["DEF"] or n_def > rules["xi_max"]["DEF"]:
            continue
        if n_mid < rules["xi_min"]["MID"] or n_mid > rules["xi_max"]["MID"]:
            continue
        if n_fwd < rules["xi_min"]["FWD"] or n_fwd > rules["xi_max"]["FWD"]:
            continue
        if len(by_pos["GKP"]) < 1 or len(by_pos["DEF"]) < n_def:
            continue
        if len(by_pos["MID"]) < n_mid or len(by_pos["FWD"]) < n_fwd:
            continue
        xi = by_pos["GKP"][:1] + by_pos["DEF"][:n_def] + by_pos["MID"][:n_mid] + by_pos["FWD"][:n_fwd]
        chosen = {p["element"] for p in xi}
        bench = [p for p in squad if p["element"] not in chosen]
        bench.sort(key=lambda p: (0 if p["position"] == "GKP" else 1, -p["xpts_gw"]))
        # FPL bench: 3 outfield in xPts order, then unused GK last
        outfield_bench = [p for p in bench if p["position"] != "GKP"]
        gk_bench = [p for p in bench if p["position"] == "GKP"]
        ordered_bench = outfield_bench + gk_bench
        score = _xi_score(xi, ordered_bench)
        if best is None or score > best["score"]:
            xi_sorted = sorted(xi, key=lambda p: (-p["xpts_gw"], p["element"]))
            captain = xi_sorted[0]
            vice = xi_sorted[1] if len(xi_sorted) > 1 else captain
            best = {
                "xi": xi,
                "bench": ordered_bench,
                "captain": captain,
                "vice": vice,
                "formation": f"{n_def}-{n_mid}-{n_fwd}",
                "score": score,
                "xpts_xi": round(sum(p["xpts_gw"] for p in xi) + captain["xpts_gw"], 4),
            }
    if best is None:
        raise ValueError("no legal starting XI")
    return best


def _cheapest_legal(players: list[dict], rules: dict) -> list[dict]:
    selected: list[dict] = []
    pos_n = defaultdict(int)
    team_n = defaultdict(int)
    cost = 0
    for player in sorted(players, key=lambda p: (p["now_cost"], -p["xpts_gw"], p["element"])):
        if pos_n[player["position"]] >= rules["squad_n"][player["position"]]:
            continue
        if team_n[player["team"]] >= rules["team_limit"]:
            continue
        if cost + player["now_cost"] > rules["budget"]:
            continue
        selected.append(player)
        pos_n[player["position"]] += 1
        team_n[player["team"]] += 1
        cost += player["now_cost"]
        if len(selected) == rules["size"]:
            break
    if not _legal_squad(selected, rules):
        raise ValueError("could not build a legal £100m squad from the player pool")
    return selected


def _try_swap(selected: list[dict], incoming: dict, rules: dict) -> list[dict] | None:
    selected_ids = {p["element"] for p in selected}
    if incoming["element"] in selected_ids:
        return None
    best_swap = None
    best_score = _xi_score(*_xi_parts(selected, rules))
    for i, outgoing in enumerate(selected):
        if outgoing["position"] != incoming["position"]:
            continue
        trial = selected[:i] + [incoming] + selected[i + 1 :]
        if not _legal_squad(trial, rules):
            continue
        xi, bench = _xi_parts(trial, rules)
        score = _xi_score(xi, bench)
        if score > best_score:
            best_score = score
            best_swap = trial
    return best_swap


def _xi_parts(squad: list[dict], rules: dict) -> tuple[list[dict], list[dict]]:
    packed = best_xi(squad, rules)
    return packed["xi"], packed["bench"]


def select_squad(players: list[dict], rules: dict | None = None, max_swaps: int = 400) -> dict:
    """Pick a legal 15, starting XI, captain and vice under FPL squad rules."""
    rules = rules or squad_rules()
    pool = [p for p in players if p["position"] in rules["squad_n"]]
    selected = _cheapest_legal(pool, rules)
    unused = [p for p in sorted(pool, key=lambda p: (-p["xpts_gw"], p["now_cost"])) if p["element"] not in {s["element"] for s in selected}]
    swaps = 0
    improved = True
    while improved and swaps < max_swaps:
        improved = False
        for incoming in unused:
            trial = _try_swap(selected, incoming, rules)
            if trial is None:
                continue
            selected = trial
            unused = [p for p in pool if p["element"] not in {s["element"] for s in selected}]
            unused.sort(key=lambda p: (-p["xpts_gw"], p["now_cost"]))
            improved = True
            swaps += 1
            break
    packed = best_xi(selected, rules)
    cost = sum(p["now_cost"] for p in selected)
    players_out = []
    for player in packed["xi"]:
        players_out.append({**player, "starter": True, "bench_order": 0})
    for i, player in enumerate(packed["bench"], start=1):
        players_out.append({**player, "starter": False, "bench_order": i})
    return {
        "players": players_out,
        "captain_element": packed["captain"]["element"],
        "vice_element": packed["vice"]["element"],
        "formation": packed["formation"],
        "cost_tenths": cost,
        "bank_tenths": rules["budget"] - cost,
        "xpts_xi": packed["xpts_xi"],
        "n_transfers": 0,
    }


def finalise_squad(owned: list[dict], rules: dict | None = None, n_transfers: int = 0) -> dict:
    rules = rules or squad_rules()
    if not _legal_squad(owned, rules):
        raise ValueError("owned players are not a legal FPL squad")
    packed = best_xi(owned, rules)
    cost = sum(p["now_cost"] for p in owned)
    players_out = [{**p, "starter": True, "bench_order": 0} for p in packed["xi"]]
    for i, player in enumerate(packed["bench"], start=1):
        players_out.append({**player, "starter": False, "bench_order": i})
    return {
        "players": players_out,
        "captain_element": packed["captain"]["element"],
        "vice_element": packed["vice"]["element"],
        "formation": packed["formation"],
        "cost_tenths": cost,
        "bank_tenths": rules["budget"] - cost,
        "xpts_xi": packed["xpts_xi"],
        "n_transfers": n_transfers,
    }


def apply_one_transfer(current: list[dict], players: list[dict], rules: dict | None = None) -> dict:
    """Keep the previous 15 and use at most one free transfer, then re-pick the XI."""
    rules = rules or squad_rules()
    current_ids = {p["element"] for p in current}
    pool = {p["element"]: p for p in players}
    owned = []
    for player in current:
        fresh = pool.get(player["element"])
        if fresh is None:
            owned.append({k: player[k] for k in ("element", "name", "team", "position", "now_cost", "xpts_gw", "expected_minutes") if k in player})
        else:
            owned.append({k: fresh[k] for k in ("element", "name", "team", "position", "now_cost", "xpts_gw", "expected_minutes")})
    best = finalise_squad(owned, rules, n_transfers=0)
    for outgoing in owned:
        for incoming in players:
            if incoming["element"] in current_ids:
                continue
            trial_owned = [
                {k: p[k] for k in ("element", "name", "team", "position", "now_cost", "xpts_gw", "expected_minutes")}
                for p in owned
                if p["element"] != outgoing["element"]
            ] + [{k: incoming[k] for k in ("element", "name", "team", "position", "now_cost", "xpts_gw", "expected_minutes")}]
            if not _legal_squad(trial_owned, rules):
                continue
            packed = finalise_squad(trial_owned, rules, n_transfers=1)
            if packed["xpts_xi"] > best["xpts_xi"]:
                best = packed
    return best


def apply_autosubs(players: list[dict], live: dict[int, dict], event_finished: bool) -> list[dict]:
    """Replace blanked starters from the bench if the Gameweek is finished. Formation must stay legal."""
    rules = squad_rules()
    starters = [p for p in players if p.get("starter")]
    bench = [p for p in sorted(players, key=lambda r: r.get("bench_order") or 99) if not p.get("starter")]
    if not event_finished:
        return starters
    used_bench: set[int] = set()
    playing = list(starters)
    for idx, starter in enumerate(starters):
        minutes = int(live.get(int(starter["element"]), {}).get("minutes") or 0)
        if minutes > 0:
            continue
        replacement = None
        for sub in bench:
            if sub["element"] in used_bench:
                continue
            if int(live.get(int(sub["element"]), {}).get("minutes") or 0) <= 0:
                continue
            if starter["position"] == "GKP" and sub["position"] != "GKP":
                continue
            if starter["position"] != "GKP" and sub["position"] == "GKP":
                continue
            trial = list(playing)
            trial[idx] = sub
            pos = _counts(trial, "position")
            if pos.get("GKP", 0) != 1:
                continue
            if not (rules["xi_min"]["DEF"] <= pos.get("DEF", 0) <= rules["xi_max"]["DEF"]):
                continue
            if not (rules["xi_min"]["MID"] <= pos.get("MID", 0) <= rules["xi_max"]["MID"]):
                continue
            if not (rules["xi_min"]["FWD"] <= pos.get("FWD", 0) <= rules["xi_max"]["FWD"]):
                continue
            replacement = sub
            break
        if replacement is not None:
            used_bench.add(replacement["element"])
            playing[idx] = replacement
    return playing


def score_squad(players: list[dict], captain_element: int, vice_element: int, live: dict[int, dict], event_finished: bool) -> dict:
    playing = apply_autosubs(players, live, event_finished)
    points = 0.0
    captain_mins = int(live.get(captain_element, {}).get("minutes") or 0)
    double = captain_element if captain_mins > 0 else vice_element
    if int(live.get(double, {}).get("minutes") or 0) <= 0:
        double = None
    for player in playing:
        pts = float(live.get(int(player["element"]), {}).get("points") or 0)
        if double is not None and int(player["element"]) == int(double):
            pts *= 2
        points += pts
    return {"actual_points": round(points, 1), "playing": playing, "doubled": double}
