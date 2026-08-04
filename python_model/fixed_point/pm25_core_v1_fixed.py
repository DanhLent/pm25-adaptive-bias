#!/usr/bin/env python3
"""Bit-accurate integer reference for pm25_core_v1_adaptive_bias_fixed."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "training" / "configs" / "core_v1_config.json"


def _load_active_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("synthetic_data") is not False:
        raise ValueError("Active core v1 config must be based on real data.")
    if config.get("config_role") != "active_pilot_config":
        raise ValueError("Active core v1 config has not been promoted for fixed-point use.")
    if config.get("promoted_to_active_config") is not True:
        raise ValueError("Active core v1 config promotion flag is not true.")
    return config


ACTIVE_CONFIG = _load_active_config()
ALGORITHM_NAME = "pm25_core_v1_adaptive_bias_fixed"

PM25_SCALE = int(ACTIVE_CONFIG["scale"])
BIAS_SHIFT = int(ACTIVE_CONFIG["selected_alpha_shift"])


def _config_value_x16(value: object) -> int:
    return int(round(float(value) * PM25_SCALE))


PM25_MIN_X16 = _config_value_x16(ACTIVE_CONFIG["pm25_min"])
PM25_MAX_X16 = _config_value_x16(ACTIVE_CONFIG["pm25_max"])
BIAS_MIN_X16 = _config_value_x16(ACTIVE_CONFIG["bias_min"])
BIAS_MAX_X16 = _config_value_x16(ACTIVE_CONFIG["bias_max"])

_THRESHOLDS = ACTIVE_CONFIG["alert_thresholds"]
GOOD_MAX_X16 = _config_value_x16(_THRESHOLDS["good_max"])
MODERATE_MAX_X16 = _config_value_x16(_THRESHOLDS["moderate_max"])
USG_MAX_X16 = _config_value_x16(_THRESHOLDS["usg_max"])
UNHEALTHY_MAX_X16 = _config_value_x16(_THRESHOLDS["unhealthy_max"])
ALERT_ON_X16 = _config_value_x16(ACTIVE_CONFIG["alert_on"])
ALERT_OFF_X16 = _config_value_x16(ACTIVE_CONFIG["alert_off"])


def float_to_x16(value: float | int) -> int:
    """Convert a boundary/input value to x16 using Python round semantics."""
    return int(round(float(value) * PM25_SCALE))


def saturate(value: int, low: int, high: int) -> int:
    """Clamp an integer to the inclusive [low, high] range."""
    if low > high:
        raise ValueError("Saturation low bound must not exceed high bound.")
    if value < low:
        return low
    if value > high:
        return high
    return value


def classify_alert_level(fused_pm25_x16: int) -> int:
    """Return the frozen alert-level encoding for a saturated x16 value."""
    if fused_pm25_x16 <= GOOD_MAX_X16:
        return 0
    if fused_pm25_x16 <= MODERATE_MAX_X16:
        return 1
    if fused_pm25_x16 <= USG_MAX_X16:
        return 2
    if fused_pm25_x16 <= UNHEALTHY_MAX_X16:
        return 3
    return 4


def update_hysteresis(prev_alert: int, fused_pm25_x16: int) -> int:
    """Apply inclusive on/off thresholds to the previous binary state."""
    if prev_alert not in (0, 1):
        raise ValueError("Previous hysteresis alert must be 0 or 1.")
    if prev_alert == 0 and fused_pm25_x16 >= ALERT_ON_X16:
        return 1
    if prev_alert == 1 and fused_pm25_x16 <= ALERT_OFF_X16:
        return 0
    return prev_alert


@dataclass(frozen=True)
class PM25Sample:
    sample_valid: int
    qc_ok: int
    hour: int
    cams_pm25_x16: int
    purpleair_pm25_x16: int


def _require_integer(name: str, value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}.")
    return value


def _normalize_sample(sample: PM25Sample | Mapping[str, int]) -> PM25Sample:
    if isinstance(sample, PM25Sample):
        values: Mapping[str, object] = {
            "sample_valid": sample.sample_valid,
            "qc_ok": sample.qc_ok,
            "hour": sample.hour,
            "cams_pm25_x16": sample.cams_pm25_x16,
            "purpleair_pm25_x16": sample.purpleair_pm25_x16,
        }
    else:
        required = (
            "sample_valid",
            "qc_ok",
            "hour",
            "cams_pm25_x16",
            "purpleair_pm25_x16",
        )
        missing = [name for name in required if name not in sample]
        if missing:
            raise KeyError(f"Missing sample fields: {', '.join(missing)}")
        values = sample

    normalized = PM25Sample(
        sample_valid=_require_integer("sample_valid", values["sample_valid"]),
        qc_ok=_require_integer("qc_ok", values["qc_ok"]),
        hour=_require_integer("hour", values["hour"]),
        cams_pm25_x16=_require_integer(
            "cams_pm25_x16", values["cams_pm25_x16"]
        ),
        purpleair_pm25_x16=_require_integer(
            "purpleair_pm25_x16", values["purpleair_pm25_x16"]
        ),
    )

    if normalized.sample_valid not in (0, 1):
        raise ValueError("sample_valid must be 0 or 1.")
    if normalized.qc_ok not in (0, 1):
        raise ValueError("qc_ok must be 0 or 1.")
    if not 0 <= normalized.hour <= 23:
        raise ValueError("hour must be in the inclusive range 0..23.")
    return normalized


class PM25CoreV1Fixed:
    """Stateful integer model whose step timing is the RTL contract."""

    def __init__(
        self,
        *,
        alpha_shift: int = BIAS_SHIFT,
        initial_bias_x16: int = 0,
        initial_hysteresis_alert: int = 0,
        sample_index: int = 0,
    ) -> None:
        if alpha_shift not in {2, 3, 4, 5, 6}:
            raise ValueError("alpha_shift must be one of 2, 3, 4, 5, or 6.")
        if initial_hysteresis_alert not in {0, 1}:
            raise ValueError("initial_hysteresis_alert must be 0 or 1.")
        self.alpha_shift = int(alpha_shift)
        self.learned_bias_x16 = saturate(
            _require_integer("initial_bias_x16", initial_bias_x16),
            BIAS_MIN_X16,
            BIAS_MAX_X16,
        )
        self.hysteresis_alert = int(initial_hysteresis_alert)
        self.sample_index = _require_integer("sample_index", sample_index)

    def reset(self) -> None:
        self.learned_bias_x16 = 0
        self.hysteresis_alert = 0
        self.sample_index = 0

    def step(self, sample: PM25Sample | Mapping[str, int]) -> dict[str, int]:
        """Process one transaction using integer arithmetic only.

        The current fused output uses learned_bias_before_x16. Any accepted
        bias update becomes state for the next call. Python signed >> is the
        frozen match for Verilog signed >>>.
        """
        current = _normalize_sample(sample)

        sample_index = self.sample_index
        sample_valid = current.sample_valid
        qc_ok = current.qc_ok
        learned_bias_before_x16 = self.learned_bias_x16
        hysteresis_alert_before = self.hysteresis_alert

        residual_x16 = current.purpleair_pm25_x16 - current.cams_pm25_x16
        error_x16 = residual_x16 - learned_bias_before_x16
        fused_raw_x16 = current.cams_pm25_x16 + learned_bias_before_x16
        fused_pm25_x16 = saturate(
            fused_raw_x16,
            PM25_MIN_X16,
            PM25_MAX_X16,
        )
        alert_level = classify_alert_level(fused_pm25_x16)

        result_valid = sample_valid
        accepted = 1 if sample_valid == 1 and qc_ok == 1 else 0

        if sample_valid == 1:
            hysteresis_alert_after = update_hysteresis(
                hysteresis_alert_before,
                fused_pm25_x16,
            )
        else:
            hysteresis_alert_after = hysteresis_alert_before

        if accepted == 1:
            delta_x16 = error_x16 >> self.alpha_shift
            learned_bias_after_x16 = saturate(
                learned_bias_before_x16 + delta_x16,
                BIAS_MIN_X16,
                BIAS_MAX_X16,
            )
        else:
            delta_x16 = 0
            learned_bias_after_x16 = learned_bias_before_x16

        self.learned_bias_x16 = learned_bias_after_x16
        self.hysteresis_alert = hysteresis_alert_after
        self.sample_index = sample_index + 1

        return {
            "sample_index": sample_index,
            "sample_valid": sample_valid,
            "qc_ok": qc_ok,
            "accepted": accepted,
            "hour": current.hour,
            "cams_pm25_x16": current.cams_pm25_x16,
            "purpleair_pm25_x16": current.purpleair_pm25_x16,
            "learned_bias_before_x16": learned_bias_before_x16,
            "residual_x16": residual_x16,
            "error_x16": error_x16,
            "delta_x16": delta_x16,
            "learned_bias_after_x16": learned_bias_after_x16,
            "fused_raw_x16": fused_raw_x16,
            "fused_pm25_x16": fused_pm25_x16,
            "alert_level": alert_level,
            "hysteresis_alert_before": hysteresis_alert_before,
            "hysteresis_alert_after": hysteresis_alert_after,
            "result_valid": result_valid,
            "alpha_shift": self.alpha_shift,
        }

    def export_state(self) -> dict[str, int]:
        return {
            "bias_x16": self.learned_bias_x16,
            "hysteresis_state": self.hysteresis_alert,
            "sample_index": self.sample_index,
            "active_alpha_shift": self.alpha_shift,
        }


__all__ = [
    "ACTIVE_CONFIG",
    "ALGORITHM_NAME",
    "ALERT_OFF_X16",
    "ALERT_ON_X16",
    "BIAS_MAX_X16",
    "BIAS_MIN_X16",
    "BIAS_SHIFT",
    "CONFIG_PATH",
    "GOOD_MAX_X16",
    "MODERATE_MAX_X16",
    "PM25CoreV1Fixed",
    "PM25Sample",
    "PM25_MAX_X16",
    "PM25_MIN_X16",
    "PM25_SCALE",
    "UNHEALTHY_MAX_X16",
    "USG_MAX_X16",
    "classify_alert_level",
    "float_to_x16",
    "saturate",
    "update_hysteresis",
]
