#!/usr/bin/env python3
"""Generate deterministic CSV vectors for the frozen core v1 integer model."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pm25_core_v1_fixed import (
    ALERT_OFF_X16,
    ALERT_ON_X16,
    GOOD_MAX_X16,
    MODERATE_MAX_X16,
    PM25CoreV1Fixed,
    PM25_MAX_X16,
    UNHEALTHY_MAX_X16,
    USG_MAX_X16,
    float_to_x16,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "test_vectors"

VECTOR_COLUMNS = [
    "sample_index",
    "sample_valid",
    "qc_ok",
    "hour",
    "cams_pm25_x16",
    "purpleair_pm25_x16",
    "result_valid",
    "accepted",
    "learned_bias_before_x16",
    "residual_x16",
    "error_x16",
    "delta_x16",
    "learned_bias_after_x16",
    "fused_raw_x16",
    "fused_pm25_x16",
    "alert_level",
    "hysteresis_alert_before",
    "hysteresis_alert_after",
]


def integer_sample(
    cams_pm25_x16: int,
    purpleair_pm25_x16: int,
    *,
    hour: int = 0,
    sample_valid: int = 1,
    qc_ok: int = 1,
) -> dict[str, int]:
    return {
        "sample_valid": sample_valid,
        "qc_ok": qc_ok,
        "hour": hour,
        "cams_pm25_x16": cams_pm25_x16,
        "purpleair_pm25_x16": purpleair_pm25_x16,
    }


def float_sample(
    cams_pm25: float,
    purpleair_pm25: float,
    *,
    hour: int = 0,
    sample_valid: int = 1,
    qc_ok: int = 1,
) -> dict[str, int]:
    return integer_sample(
        float_to_x16(cams_pm25),
        float_to_x16(purpleair_pm25),
        hour=hour,
        sample_valid=sample_valid,
        qc_ok=qc_ok,
    )


def build_scenarios() -> dict[str, list[dict[str, int]]]:
    threshold_values = [
        GOOD_MAX_X16 - 1,
        GOOD_MAX_X16,
        GOOD_MAX_X16 + 1,
        MODERATE_MAX_X16 - 1,
        MODERATE_MAX_X16,
        MODERATE_MAX_X16 + 1,
        USG_MAX_X16 - 1,
        USG_MAX_X16,
        USG_MAX_X16 + 1,
        UNHEALTHY_MAX_X16 - 1,
        UNHEALTHY_MAX_X16,
        UNHEALTHY_MAX_X16 + 1,
    ]
    hysteresis_values = [
        ALERT_OFF_X16 - 1,
        ALERT_ON_X16 - 1,
        ALERT_ON_X16,
        ALERT_ON_X16 - 1,
        ALERT_OFF_X16 + 1,
        ALERT_OFF_X16,
        ALERT_ON_X16,
        ALERT_OFF_X16 + 1,
        ALERT_OFF_X16 - 1,
    ]
    mixed_real_like = [
        (28.0, 18.0, 1),
        (29.5, 20.0, 0),
        (31.0, 22.5, 1),
        (34.0, 26.0, 1),
        (37.0, 29.0, 0),
        (40.0, 32.0, 1),
        (36.0, 27.5, 0),
        (33.0, 24.0, 1),
        (30.0, 20.5, 1),
        (27.0, 17.0, 0),
        (25.0, 15.0, 1),
        (29.0, 19.5, 1),
        (35.0, 26.0, 0),
        (39.0, 30.0, 1),
        (32.0, 23.0, 0),
        (28.0, 18.5, 1),
    ]

    return {
        "core_v1_zero_residual.csv": [
            float_sample(25.0, 25.0, hour=index) for index in range(8)
        ],
        "core_v1_constant_positive_residual.csv": [
            float_sample(25.0, 33.0, hour=index % 24) for index in range(12)
        ],
        "core_v1_constant_negative_residual.csv": [
            float_sample(30.0, 20.0, hour=index % 24) for index in range(12)
        ],
        "core_v1_invalid_and_qc_hold.csv": [
            integer_sample(400, 800, hour=0),
            integer_sample(900, 0, hour=1, sample_valid=0),
            integer_sample(ALERT_ON_X16, ALERT_ON_X16 + 1000, hour=2, qc_ok=0),
            integer_sample(ALERT_ON_X16 - 10, ALERT_ON_X16 + 1000, hour=3, qc_ok=0),
            integer_sample(0, 0, hour=4, sample_valid=0, qc_ok=0),
            integer_sample(ALERT_OFF_X16 - 100, ALERT_OFF_X16 - 100, hour=5, qc_ok=0),
            integer_sample(600, 200, hour=6),
            integer_sample(0, 900, hour=7, sample_valid=0),
        ],
        "core_v1_threshold_boundaries.csv": [
            integer_sample(value, value, hour=index % 24, qc_ok=0)
            for index, value in enumerate(threshold_values)
        ],
        "core_v1_hysteresis.csv": [
            integer_sample(value, value, hour=index % 24, qc_ok=0)
            for index, value in enumerate(hysteresis_values)
        ],
        "core_v1_bias_saturation.csv": [
            integer_sample(0, 100000, hour=0),
            integer_sample(0, 100000, hour=1),
            integer_sample(100000, 0, hour=2),
            integer_sample(100000, 0, hour=3),
        ],
        "core_v1_output_saturation.csv": [
            integer_sample(65536, 0, hour=0),
            integer_sample(0, 0, hour=1, qc_ok=0),
            integer_sample(0, 65536, hour=2),
            integer_sample(PM25_MAX_X16, PM25_MAX_X16, hour=3, qc_ok=0),
            integer_sample(PM25_MAX_X16 + 500, PM25_MAX_X16 + 500, hour=4, qc_ok=0),
        ],
        "core_v1_negative_shift.csv": [
            integer_sample(100, 85, hour=0),
            integer_sample(100, 82, hour=1),
            integer_sample(100, 112, hour=2),
            integer_sample(100, 83, hour=3),
        ],
        "core_v1_mixed_real_like_scenario.csv": [
            float_sample(cams, purpleair, hour=index % 24, qc_ok=qc_ok)
            for index, (cams, purpleair, qc_ok) in enumerate(mixed_real_like)
        ],
    }


def write_scenario(path: Path, samples: list[dict[str, int]]) -> int:
    core = PM25CoreV1Fixed()
    rows = [core.step(sample) for sample in samples]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=VECTOR_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in VECTOR_COLUMNS})
    return len(rows)


def main() -> None:
    counts = {
        filename: write_scenario(OUTPUT_DIR / filename, samples)
        for filename, samples in build_scenarios().items()
    }
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
