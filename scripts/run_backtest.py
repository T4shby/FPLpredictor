#!/usr/bin/env python
"""Walk-forward backtest for Models A–D."""

from __future__ import annotations

import argparse

from backtest.engine import run_all_models, write_report
from modelling.predict import ALL_MODELS, MODEL_A, MODEL_B, MODEL_C, MODEL_D


MODELS = {"A": MODEL_A, "B": MODEL_B, "C": MODEL_C, "D": MODEL_D}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default=None)
    parser.add_argument("--models", default="A,B,C,D")
    parser.add_argument("--no-prior", action="store_true")
    args = parser.parse_args()
    specs = [MODELS[key.strip()] for key in args.models.split(",") if key.strip() in MODELS]
    results = run_all_models(season=args.season, include_prior=not args.no_prior, models=specs or ALL_MODELS)
    path = write_report(results)
    print(path)
    for result in results:
        print(result.model_key, result.metrics)


if __name__ == "__main__":
    main()
