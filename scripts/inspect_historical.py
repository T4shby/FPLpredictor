#!/usr/bin/env python
"""Inspect cached historical files and write a data dictionary."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.app.core.settings import get_settings
from data.ingestion.historical import load_fixtures, load_merged_gameweeks, load_teams
from data.validation.validators import summarise_frame, validate_player_gameweeks


FEATURE_CATALOG = [
    ("minutes", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "Playing time"),
    ("starts", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "Start flag"),
    ("total_points", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "Actual FPL points"),
    ("goals_scored", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "Goals"),
    ("assists", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "Assists"),
    ("expected_goals", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "Player xG"),
    ("expected_assists", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "Player xA"),
    ("expected_goals_conceded", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "Player xGC"),
    ("defensive_contribution", "DIRECTLY AVAILABLE", "vaastav merged_gw / FPL live", "DEFCON FPL points"),
    ("clearances_blocks_interceptions", "DIRECTLY AVAILABLE", "vaastav / FPL live", "CBIT count"),
    ("recoveries", "DIRECTLY AVAILABLE", "vaastav / FPL live", "Ball recoveries"),
    ("tackles", "DIRECTLY AVAILABLE", "vaastav / FPL live", "Tackles"),
    ("bonus", "DIRECTLY AVAILABLE", "vaastav / FPL live", "Bonus points"),
    ("bps", "DIRECTLY AVAILABLE", "vaastav / FPL live", "Bonus point system score"),
    ("saves", "DIRECTLY AVAILABLE", "vaastav / FPL live", "GK saves"),
    ("value", "DIRECTLY AVAILABLE", "vaastav merged_gw", "Price in tenths of a million at that GW"),
    ("selected", "DIRECTLY AVAILABLE", "vaastav merged_gw", "Ownership count/percent depending on file"),
    ("chance_of_playing_next_round", "DIRECTLY AVAILABLE", "FPL live bootstrap only", "Not in historical merged_gw"),
    ("penalties_order", "DIRECTLY AVAILABLE", "FPL live bootstrap", "Historical penalty taker flag is incomplete"),
    ("pp90_l3", "DERIVED", "rolling features", "Points per 90 over last 3 GWs"),
    ("attack_rating", "DERIVED", "team strength", "Goals-based attack rating"),
    ("xg_attack_rating", "DERIVED", "team strength", "xG-based attack rating"),
    ("attack_fixture_rating", "DERIVED", "fixture model", "0-100 attacking fixture rating"),
    ("defence_fixture_rating", "DERIVED", "fixture model", "0-100 defensive fixture rating"),
    ("expected_minutes", "DERIVED", "minutes heuristic", "Explainable minutes model"),
    ("team_xg", "DERIVED", "Poisson/attack-defence", "Expected team goals in this fixture"),
    ("p_clean_sheet", "DERIVED", "Poisson P(0)", "Clean sheet probability"),
    ("h2h_goals_for", "DERIVED", "previous meetings", "Shrunk H2H feature"),
    ("championship_xg", "NOT CURRENTLY AVAILABLE", "external", "Promoted-team Championship xG not ingested"),
    ("european_fixtures", "NOT CURRENTLY AVAILABLE", "external", "UEFA rest/congestion not ingested"),
    ("set_piece_taker_history", "EXTERNAL SOURCE REQUIRED", "FPL live has order fields; historical incomplete", "Use live penalties_order"),
]


def main() -> None:
    settings = get_settings()
    season = settings.historical_season
    gw = load_merged_gameweeks(season, download=True)
    teams = load_teams(season, download=True)
    fixtures = load_fixtures(season, download=True)
    validation = validate_player_gameweeks(gw)
    summary = summarise_frame(gw)
    docs = Path("docs")
    docs.mkdir(exist_ok=True)
    dictionary = {
        "season": season,
        "validation_ok": validation.ok,
        "validation_errors": validation.errors,
        "validation_warnings": validation.warnings,
        "player_gameweek_rows": summary["rows"],
        "player_gameweek_columns": summary["columns"],
        "null_counts": summary["null_counts"],
        "unique_players": int(gw["element"].nunique()),
        "unique_teams": int(gw["team"].nunique()) if "team" in gw.columns else None,
        "gameweeks": sorted(int(x) for x in gw["GW"].dropna().unique()),
        "teams_file_rows": int(len(teams)),
        "fixtures_file_rows": int(len(fixtures)),
        "feature_catalog": [
            {"field": name, "classification": klass, "source": source, "notes": notes}
            for name, klass, source, notes in FEATURE_CATALOG
        ],
    }
    out = docs / "DATA_DICTIONARY.md"
    lines = [
        f"# Data dictionary — {season}",
        "",
        f"Rows: **{dictionary['player_gameweek_rows']}**",
        f"Players: **{dictionary['unique_players']}**",
        f"Gameweeks: **{dictionary['gameweeks'][0]}–{dictionary['gameweeks'][-1]}** ({len(dictionary['gameweeks'])} unique)",
        f"Validation: **{'OK' if validation.ok else 'FAILED'}**",
        "",
        "## Columns in merged_gw",
        "",
        "| Column | Non-null | Nulls |",
        "| --- | ---: | ---: |",
    ]
    for col in summary["columns"]:
        nulls = summary["null_counts"][col]
        lines.append(f"| `{col}` | {summary['rows'] - nulls} | {nulls} |")
    lines.extend(["", "## Feature classification", "", "| Field | Class | Source | Notes |", "| --- | --- | --- | --- |"])
    for item in dictionary["feature_catalog"]:
        lines.append(f"| `{item['field']}` | {item['classification']} | {item['source']} | {item['notes']} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (docs / "data_dictionary.json").write_text(json.dumps(dictionary, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
