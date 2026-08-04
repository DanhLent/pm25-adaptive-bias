#!/usr/bin/env python3
"""Generate deterministic hourly PM2.5 data for the training-stage smoke test."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timedelta
from pathlib import Path


def build_rows(row_count: int = 96) -> list[dict[str, object]]:
    """Return a deterministic synthetic CAMS/PurpleAir sequence."""
    start = datetime(2026, 1, 1, 0, 0, 0)
    rows: list[dict[str, object]] = []

    for index in range(row_count):
        timestamp = start + timedelta(hours=index)
        hour = timestamp.hour

        daily_background = 4.2 * math.sin(2.0 * math.pi * (hour - 5) / 24.0)
        slow_drift = 0.035 * index
        cams_pm25 = 27.0 + daily_background + slow_drift

        residual = 3.5 + 0.55 * math.sin(2.0 * math.pi * index / 48.0)
        if 6 <= hour <= 9:
            residual += 5.0
        if 17 <= hour <= 21:
            residual += 7.0

        deterministic_noise = (((index * 17) % 13) - 6) * 0.18
        purpleair_pm25 = cams_pm25 + residual + deterministic_noise
        qc_ok = 0 if index in {11, 38, 65, 92} else 1

        rows.append(
            {
                "timestamp": timestamp.isoformat(),
                "hour": hour,
                "cams_pm25": round(cams_pm25, 3),
                "purpleair_pm25": round(purpleair_pm25, 3),
                "qc_ok": qc_ok,
            }
        )

    return rows


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["timestamp", "hour", "cams_pm25", "purpleair_pm25", "qc_ok"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create deterministic four-day PM2.5 training data."
    )
    parser.add_argument(
        "--output",
        default="training/outputs/sample_training_data.csv",
        help="Destination CSV path.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=96,
        help="Number of hourly rows to create; must be at least 96.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.rows < 96:
        raise ValueError("--rows must be at least 96 so the sample spans four days.")

    output_path = Path(args.output)
    rows = build_rows(args.rows)
    write_rows(output_path, rows)
    invalid_count = sum(1 for row in rows if not int(row["qc_ok"]))
    print(
        f"Wrote {len(rows)} rows to {output_path} "
        f"({invalid_count} rows have qc_ok=0)."
    )


if __name__ == "__main__":
    main()
