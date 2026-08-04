#!/usr/bin/env python3
"""Generate extra deterministic CSV vectors for RTL quality review."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from pm25_core_v1_fixed import (
    ALERT_OFF_X16,
    ALERT_ON_X16,
    BIAS_MAX_X16,
    BIAS_MIN_X16,
    PM25CoreV1Fixed,
    PM25_MAX_X16,
    PM25_MIN_X16,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "test_vectors" / "extra"
RANDOM_SEED = 1

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


def extra_long_positive_adaptation() -> list[dict[str, int]]:
    return [
        integer_sample(400, 656, hour=index % 24)
        for index in range(128)
    ]


def extra_long_negative_adaptation() -> list[dict[str, int]]:
    return [
        integer_sample(640, 320, hour=index % 24)
        for index in range(128)
    ]


def extra_qc_burst_hold() -> list[dict[str, int]]:
    samples: list[dict[str, int]] = []
    for block in range(10):
        samples.append(
            integer_sample(
                420 + block * 8,
                700 + block * 8,
                hour=len(samples) % 24,
                qc_ok=1,
            )
        )
        for burst_index in range(9):
            cams = ALERT_ON_X16 + ((burst_index % 3) - 1) * 20
            samples.append(
                integer_sample(
                    cams,
                    cams + 500 - block * 5,
                    hour=len(samples) % 24,
                    qc_ok=0,
                )
            )
    return samples


def extra_invalid_burst_hold() -> list[dict[str, int]]:
    samples: list[dict[str, int]] = [
        integer_sample(ALERT_ON_X16 + 32, ALERT_ON_X16 + 200, hour=0, qc_ok=0),
        integer_sample(420, 720, hour=1, qc_ok=1),
    ]
    invalid_values = [
        (ALERT_ON_X16 + 700, ALERT_ON_X16 + 1200),
        (ALERT_OFF_X16 - 300, ALERT_OFF_X16 - 900),
        (PM25_MAX_X16 + 1000, 0),
        (PM25_MIN_X16, PM25_MAX_X16 + 500),
    ]
    for block in range(6):
        samples.append(
            integer_sample(
                450 + block * 10,
                720 + block * 10,
                hour=len(samples) % 24,
                qc_ok=1,
            )
        )
        for burst_index in range(12):
            cams, purpleair = invalid_values[burst_index % len(invalid_values)]
            samples.append(
                integer_sample(
                    cams,
                    purpleair,
                    hour=len(samples) % 24,
                    sample_valid=0,
                    qc_ok=burst_index % 2,
                )
            )
    samples.append(
        integer_sample(ALERT_OFF_X16 - 20, ALERT_OFF_X16 - 20, hour=len(samples) % 24, qc_ok=0)
    )
    return samples


def extra_threshold_chatter() -> list[dict[str, int]]:
    chatter_values = [
        ALERT_ON_X16 - 2,
        ALERT_ON_X16 - 1,
        ALERT_ON_X16,
        ALERT_ON_X16 - 1,
        ALERT_ON_X16 + 1,
        ALERT_OFF_X16 + 2,
        ALERT_OFF_X16 + 1,
        ALERT_OFF_X16,
        ALERT_OFF_X16 + 1,
        ALERT_ON_X16 - 1,
        ALERT_ON_X16,
        ALERT_OFF_X16 - 1,
    ]
    return [
        integer_sample(value, value, hour=index % 24, qc_ok=0)
        for index, value in enumerate(chatter_values * 5)
    ]


def extra_saturation_edges() -> list[dict[str, int]]:
    return [
        integer_sample(0, 100_000, hour=0),
        integer_sample(PM25_MAX_X16 - 1, PM25_MAX_X16 - 1, hour=1, qc_ok=0),
        integer_sample(PM25_MAX_X16, PM25_MAX_X16, hour=2, qc_ok=0),
        integer_sample(PM25_MAX_X16 + 1, PM25_MAX_X16 + 1, hour=3, qc_ok=0),
        integer_sample(BIAS_MAX_X16, BIAS_MAX_X16, hour=4, qc_ok=0),
        integer_sample(100_000, 0, hour=5),
        integer_sample(PM25_MIN_X16, PM25_MIN_X16, hour=6, qc_ok=0),
        integer_sample(PM25_MIN_X16 + 1, PM25_MIN_X16 + 1, hour=7, qc_ok=0),
        integer_sample(-100, -100, hour=8, qc_ok=0),
        integer_sample(-BIAS_MIN_X16, -BIAS_MIN_X16, hour=9, qc_ok=0),
        integer_sample(0, 100_000, hour=10),
        integer_sample(PM25_MAX_X16 - BIAS_MAX_X16 - 1, 0, hour=11, qc_ok=0),
        integer_sample(PM25_MAX_X16 - BIAS_MAX_X16, 0, hour=12, qc_ok=0),
        integer_sample(PM25_MAX_X16 - BIAS_MAX_X16 + 1, 0, hour=13, qc_ok=0),
        integer_sample(100_000, 0, hour=14),
        integer_sample(BIAS_MAX_X16 - 1, 0, hour=15, qc_ok=0),
        integer_sample(BIAS_MAX_X16, 0, hour=16, qc_ok=0),
        integer_sample(BIAS_MAX_X16 + 1, 0, hour=17, qc_ok=0),
    ]


def extra_signed_shift_edges() -> list[dict[str, int]]:
    target_errors = [
        -1,
        -2,
        -7,
        -8,
        -9,
        -15,
        -16,
        -17,
        0,
        1,
        7,
        8,
        9,
        15,
        16,
        17,
    ]
    samples: list[dict[str, int]] = []
    probe = PM25CoreV1Fixed()
    cams = 1000
    for index, target_error in enumerate(target_errors):
        residual = probe.learned_bias_x16 + target_error
        sample = integer_sample(
            cams,
            cams + residual,
            hour=index % 24,
            qc_ok=1,
        )
        samples.append(sample)
        probe.step(sample)
    return samples


def extra_random_stress_seed_1() -> list[dict[str, int]]:
    rng = random.Random(RANDOM_SEED)
    samples: list[dict[str, int]] = []
    threshold_walk = [
        ALERT_OFF_X16 - 24,
        ALERT_OFF_X16,
        ALERT_OFF_X16 + 24,
        ALERT_ON_X16 - 24,
        ALERT_ON_X16,
        ALERT_ON_X16 + 24,
    ]

    for index in range(320):
        if index % 32 < len(threshold_walk):
            cams = threshold_walk[index % 32]
        else:
            cams = max(0, min(PM25_MAX_X16 + 600, int(rng.gauss(620, 260))))

        if index % 29 == 0:
            residual = -rng.randint(180, 700)
        elif index % 31 == 0:
            residual = rng.randint(220, 850)
        else:
            residual = rng.randint(-420, 520)

        purpleair = max(0, min(PM25_MAX_X16 + 900, cams + residual))

        sample_valid = 0 if (index % 41 in (9, 10, 11) or rng.random() < 0.08) else 1
        qc_ok = 0 if (index % 37 in (5, 6, 7, 8) or rng.random() < 0.18) else 1
        if sample_valid == 0 and rng.random() < 0.5:
            qc_ok = 0

        samples.append(
            integer_sample(
                cams,
                purpleair,
                hour=index % 24,
                sample_valid=sample_valid,
                qc_ok=qc_ok,
            )
        )

    return samples


def build_scenarios() -> dict[str, list[dict[str, int]]]:
    return {
        "extra_long_positive_adaptation.csv": extra_long_positive_adaptation(),
        "extra_long_negative_adaptation.csv": extra_long_negative_adaptation(),
        "extra_qc_burst_hold.csv": extra_qc_burst_hold(),
        "extra_invalid_burst_hold.csv": extra_invalid_burst_hold(),
        "extra_threshold_chatter.csv": extra_threshold_chatter(),
        "extra_saturation_edges.csv": extra_saturation_edges(),
        "extra_signed_shift_edges.csv": extra_signed_shift_edges(),
        "extra_random_stress_seed_1.csv": extra_random_stress_seed_1(),
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
