#!/usr/bin/env python
"""Download vaastav historical FPL CSVs into data/cache (gitignored)."""

from __future__ import annotations

import argparse

from data.ingestion.historical import ensure_season_files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", action="append", dest="seasons")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    seasons = args.seasons or ["2024-25", "2025-26"]
    for season in seasons:
        paths = ensure_season_files(season, force=args.force)
        print(season)
        for key, path in paths.items():
            print(f"  {key}: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
