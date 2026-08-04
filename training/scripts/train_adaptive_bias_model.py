#!/usr/bin/env python3
"""Evaluate shift-friendly adaptive-bias candidates without promoting them."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.loading import load_config
from pm25_alert.evaluation import evaluate_alpha_candidates


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="data/processed/pm25_hourly_canonical.csv",
        help="Chronological canonical hourly CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/alpha_evaluation",
        help="Candidate report directory.",
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--minimum-valid-hours", type=int, default=16)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    if not input_path.exists():
        raise FileNotFoundError(
            f"Canonical evaluation dataset is missing: {input_path}"
        )
    report = evaluate_alpha_candidates(
        pd.read_csv(input_path),
        config=load_config(config_path),
        output_dir=output_dir,
        requested_folds=args.folds,
        minimum_valid_hours=args.minimum_valid_hours,
    )
    summary = {
        "status": report["status"],
        "valid_target_hours": report["valid_target_hours"],
        "fold_count": (
            report["aggregates"][0]["fold_count"]
            if report["aggregates"]
            else 0
        ),
        "best_observed_shift": report["best_observed_shift"],
        "active_alpha_shift": report["active_alpha_shift_after"],
        "auto_promoted": report["auto_promoted"],
        "output_dir": str(output_dir),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
