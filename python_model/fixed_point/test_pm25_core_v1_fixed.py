#!/usr/bin/env python3
"""Plain-assert and pytest-compatible tests for the frozen core v1 model."""

from __future__ import annotations

import csv
import ast
import inspect
import json
import textwrap
from pathlib import Path

from pm25_core_v1_fixed import (
    ACTIVE_CONFIG,
    ALERT_OFF_X16,
    ALERT_ON_X16,
    BIAS_MAX_X16,
    BIAS_MIN_X16,
    BIAS_SHIFT,
    CONFIG_PATH,
    GOOD_MAX_X16,
    MODERATE_MAX_X16,
    PM25CoreV1Fixed,
    PM25_MAX_X16,
    PM25_MIN_X16,
    PM25_SCALE,
    UNHEALTHY_MAX_X16,
    USG_MAX_X16,
    classify_alert_level,
    float_to_x16,
    saturate,
    update_hysteresis,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VECTOR_DIR = PROJECT_ROOT / "data" / "test_vectors"
VECTOR_FILES = (
    "core_v1_zero_residual.csv",
    "core_v1_constant_positive_residual.csv",
    "core_v1_constant_negative_residual.csv",
    "core_v1_invalid_and_qc_hold.csv",
    "core_v1_threshold_boundaries.csv",
    "core_v1_hysteresis.csv",
    "core_v1_bias_saturation.csv",
    "core_v1_output_saturation.csv",
    "core_v1_negative_shift.csv",
    "core_v1_mixed_real_like_scenario.csv",
)
EXPECTED_VECTOR_COLUMNS = {
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
}


def _sample(
    cams: int,
    purpleair: int,
    *,
    sample_valid: int = 1,
    qc_ok: int = 1,
    hour: int = 0,
) -> dict[str, int]:
    return {
        "sample_valid": sample_valid,
        "qc_ok": qc_ok,
        "hour": hour,
        "cams_pm25_x16": cams,
        "purpleair_pm25_x16": purpleair,
    }


def test_active_config() -> None:
    assert CONFIG_PATH.exists()
    loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert loaded == ACTIVE_CONFIG
    assert loaded["synthetic_data"] is False
    assert loaded["config_role"] == "active_pilot_config"
    assert loaded["promoted_to_active_config"] is True
    assert BIAS_SHIFT == 3
    assert PM25_SCALE == 16


def test_constants_x16() -> None:
    assert PM25_MIN_X16 == 0
    assert PM25_MAX_X16 == 8000
    assert BIAS_MIN_X16 == -2048
    assert BIAS_MAX_X16 == 2048
    assert GOOD_MAX_X16 == 192
    assert MODERATE_MAX_X16 == 566
    assert USG_MAX_X16 == 886
    assert UNHEALTHY_MAX_X16 == 2406
    assert ALERT_ON_X16 == 566
    assert ALERT_OFF_X16 == 512
    assert float_to_x16(0.0625) == 1


def test_saturate_helper() -> None:
    assert saturate(-1, 0, 10) == 0
    assert saturate(0, 0, 10) == 0
    assert saturate(7, 0, 10) == 7
    assert saturate(10, 0, 10) == 10
    assert saturate(11, 0, 10) == 10


def test_alert_level_boundaries() -> None:
    assert classify_alert_level(GOOD_MAX_X16) == 0
    assert classify_alert_level(GOOD_MAX_X16 + 1) == 1
    assert classify_alert_level(MODERATE_MAX_X16) == 1
    assert classify_alert_level(MODERATE_MAX_X16 + 1) == 2
    assert classify_alert_level(USG_MAX_X16) == 2
    assert classify_alert_level(USG_MAX_X16 + 1) == 3
    assert classify_alert_level(UNHEALTHY_MAX_X16) == 3
    assert classify_alert_level(UNHEALTHY_MAX_X16 + 1) == 4


def test_hysteresis_on_off_hold() -> None:
    assert update_hysteresis(0, ALERT_ON_X16 - 1) == 0
    assert update_hysteresis(0, ALERT_ON_X16) == 1
    assert update_hysteresis(1, ALERT_OFF_X16 + 1) == 1
    assert update_hysteresis(1, ALERT_OFF_X16) == 0


def test_zero_residual() -> None:
    core = PM25CoreV1Fixed()
    result = core.step(_sample(400, 400))
    assert result["residual_x16"] == 0
    assert result["delta_x16"] == 0
    assert result["learned_bias_after_x16"] == 0


def test_positive_residual_adaptation() -> None:
    core = PM25CoreV1Fixed()
    result = core.step(_sample(400, 416))
    assert result["error_x16"] == 16
    assert result["delta_x16"] == 2
    assert result["learned_bias_after_x16"] == 2


def test_negative_residual_and_shift() -> None:
    core = PM25CoreV1Fixed()
    result = core.step(_sample(100, 85))
    assert result["error_x16"] == -15
    assert result["delta_x16"] == -2
    assert 16 >> 3 == 2
    assert -16 >> 3 == -2
    assert -15 >> 3 == -2


def test_parameterized_alpha_shifts_2_through_6() -> None:
    for shift in range(2, 7):
        core = PM25CoreV1Fixed(alpha_shift=shift)
        positive = core.step(_sample(100, 164))
        assert positive["delta_x16"] == 64 >> shift
        assert positive["alpha_shift"] == shift

        negative_core = PM25CoreV1Fixed(alpha_shift=shift)
        negative = negative_core.step(_sample(164, 100))
        assert negative["delta_x16"] == -64 >> shift


def test_invalid_sample_holds_state() -> None:
    core = PM25CoreV1Fixed()
    core.learned_bias_x16 = 37
    core.hysteresis_alert = 1
    result = core.step(_sample(0, 10000, sample_valid=0))
    assert result["result_valid"] == 0
    assert result["accepted"] == 0
    assert result["delta_x16"] == 0
    assert result["learned_bias_before_x16"] == 37
    assert result["learned_bias_after_x16"] == 37
    assert result["hysteresis_alert_before"] == 1
    assert result["hysteresis_alert_after"] == 1


def test_qc_failed_holds_bias_but_result_is_valid() -> None:
    core = PM25CoreV1Fixed()
    result = core.step(_sample(ALERT_ON_X16, ALERT_ON_X16 + 1000, qc_ok=0))
    assert result["result_valid"] == 1
    assert result["accepted"] == 0
    assert result["residual_x16"] == 1000
    assert result["error_x16"] == 1000
    assert result["delta_x16"] == 0
    assert result["learned_bias_after_x16"] == 0
    assert result["hysteresis_alert_after"] == 1


def test_bias_min_max_saturation() -> None:
    core = PM25CoreV1Fixed()
    positive = core.step(_sample(0, 100000))
    assert positive["learned_bias_after_x16"] == BIAS_MAX_X16
    negative = core.step(_sample(100000, 0))
    assert negative["learned_bias_after_x16"] == BIAS_MIN_X16


def test_output_min_max_saturation() -> None:
    core = PM25CoreV1Fixed()
    core.learned_bias_x16 = BIAS_MIN_X16
    low = core.step(_sample(0, 0, qc_ok=0))
    assert low["fused_raw_x16"] == BIAS_MIN_X16
    assert low["fused_pm25_x16"] == PM25_MIN_X16

    core.learned_bias_x16 = BIAS_MAX_X16
    high = core.step(_sample(PM25_MAX_X16, PM25_MAX_X16, qc_ok=0))
    assert high["fused_raw_x16"] == PM25_MAX_X16 + BIAS_MAX_X16
    assert high["fused_pm25_x16"] == PM25_MAX_X16


def test_pre_update_bias_timing() -> None:
    core = PM25CoreV1Fixed()
    first = core.step(_sample(400, 800))
    assert first["fused_raw_x16"] == 400
    assert first["learned_bias_before_x16"] == 0
    assert first["learned_bias_after_x16"] == 50
    second = core.step(_sample(400, 800, qc_ok=0))
    assert second["fused_raw_x16"] == 450
    assert second["learned_bias_before_x16"] == 50


def test_step_is_integer_only() -> None:
    source = textwrap.dedent(inspect.getsource(PM25CoreV1Fixed.step))
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.Div) for node in ast.walk(tree))
    assert not any(
        isinstance(node, ast.Constant) and isinstance(node.value, float)
        for node in ast.walk(tree)
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(tree)
    )


def test_generated_vector_files() -> None:
    for filename in VECTOR_FILES:
        path = VECTOR_DIR / filename
        assert path.exists(), f"Missing vector file: {path}"
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames is not None
            assert EXPECTED_VECTOR_COLUMNS.issubset(set(reader.fieldnames))
            assert list(reader), f"Vector file has no data rows: {path}"


def main() -> None:
    tests = sorted(
        (name, value)
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    )
    for name, test in tests:
        test()
        print(f"PASS {name}")
    print(f"{len(tests)} tests passed.")


if __name__ == "__main__":
    main()
