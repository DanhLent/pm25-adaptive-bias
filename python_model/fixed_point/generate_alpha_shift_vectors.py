#!/usr/bin/env python3
"""Generate compile-time ALPHA_SHIFT regression vectors for shifts 2 through 6."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from generate_test_vectors_v1 import VECTOR_COLUMNS, build_scenarios
from pm25_core_v1_fixed import PM25CoreV1Fixed


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "test_vectors" / "alpha_shift"
SHIFTS = (2, 3, 4, 5, 6)


def build_alpha_samples() -> list[dict[str, int]]:
    """Reuse all directed core-v1 scenarios in a single stateful sequence."""
    samples: list[dict[str, int]] = []
    for scenario in build_scenarios().values():
        samples.extend(scenario)
    return samples


def write_shift_vector(shift: int) -> tuple[Path, int]:
    samples = build_alpha_samples()
    core = PM25CoreV1Fixed(alpha_shift=shift)
    rows = [core.step(sample) for sample in samples]
    path = OUTPUT_DIR / f"core_v1_alpha_shift_{shift}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=VECTOR_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in VECTOR_COLUMNS})
    return path, len(rows)


def main() -> None:
    result = {}
    for shift in SHIFTS:
        path, count = write_shift_vector(shift)
        result[str(shift)] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "samples": count,
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
