from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pm25_alert.fusion.alert_logic import (
    apply_binary_hysteresis,
    classify_alert_level,
    compute_dual_ema_residual,
    compute_linear_early_warning,
    compute_sensor_confidence,
    compute_single_ema_residual,
)


CFG = {
    "alert_thresholds": {"good": 12.0, "moderate": 35.4, "unhealthy_sensitive": 55.4, "unhealthy": 150.4},
    "fusion_alert": {
        "residual": {"max_abs_residual": 200.0, "max_abs_correction": 100.0, "decay_when_invalid": 0.95},
        "confidence": {
            "strict_source_weight": 1.0,
            "loose_source_weight": 0.35,
            "missing_source_weight": 0.0,
            "bad_fraction_penalty": True,
            "low_valid_sample_penalty": True,
            "min_good_valid_samples_per_hour": 10,
        },
        "single_ema": {"alpha": 0.30},
        "dual_ema": {"alpha_fast": 0.65, "alpha_slow": 0.18, "trend_gain": 0.50},
        "early_warning": {"horizons_hours": [1, 3, 6], "slope_window_hours": 3, "max_abs_slope": 50.0},
        "alert_logic": {"threshold_exceed": 35.4, "hysteresis_on": 35.4, "hysteresis_off": 32.0},
    },
}


def test_classify_alert_level():
    assert classify_alert_level(10.0, CFG["alert_thresholds"]) == "good"
    assert classify_alert_level(40.0, CFG["alert_thresholds"]) == "unhealthy_sensitive"


def test_apply_binary_hysteresis():
    states = apply_binary_hysteresis([30, 36, 34, 31], 35.4, 32.0)
    assert states == [False, True, True, False]


def test_confidence_clipping():
    row = pd.Series(
        {
            "pa_pm25_hourly": 10.0,
            "pa_pm25_hourly_source": "strict",
            "pa_bad_fraction_per_hour": -5.0,
            "pa_valid_samples_per_hour": 100,
            "pa_total_samples_per_hour": 10,
            "channel_disagree_count": 0,
        }
    )
    assert 0.0 <= compute_sensor_confidence(row, CFG) <= 1.0


def test_ema_output_length():
    df = pd.DataFrame(
        {
            "pa_pm25_hourly": [10.0, 12.0, 14.0],
            "cams_pm25": [8.0, 8.0, 8.0],
            "sensor_confidence": [1.0, 0.5, 0.0],
        }
    )
    assert len(compute_single_ema_residual(df, CFG)) == len(df)


def test_dual_ema_columns_and_length():
    df = pd.DataFrame(
        {
            "pa_pm25_hourly": [10.0, 12.0, 14.0],
            "cams_pm25": [8.0, 8.0, 8.0],
            "sensor_confidence": [1.0, 0.5, 0.0],
        }
    )
    out = compute_dual_ema_residual(df, CFG)
    expected = {
        "residual_fast_ema",
        "residual_slow_ema",
        "residual_trend_fast_minus_slow",
        "residual_dual_ema_correction",
    }
    assert expected.issubset(out.columns)
    assert len(out) == len(df)


def test_early_warning_forecasts_non_negative():
    df = pd.DataFrame({"fused_pm25_stage2": [30.0, 20.0, 10.0, 1.0]})
    out = compute_linear_early_warning(df, CFG)
    forecast_cols = [col for col in out.columns if col.startswith("forecast_pm25_")]
    assert forecast_cols
    assert (out[forecast_cols].dropna() >= 0.0).all().all()


def test_hysteresis_does_not_flicker_near_threshold():
    states = apply_binary_hysteresis([36.0, 34.0, 33.0, 34.5, 31.9], 35.4, 32.0)
    assert states == [True, True, True, True, False]


def test_loose_confidence_lower_than_strict():
    common = {
        "pa_pm25_hourly": 10.0,
        "pa_bad_fraction_per_hour": 0.2,
        "pa_valid_samples_per_hour": 10,
        "pa_total_samples_per_hour": 10,
        "channel_disagree_count": 1,
    }
    strict = compute_sensor_confidence(pd.Series({**common, "pa_pm25_hourly_source": "strict"}), CFG)
    loose = compute_sensor_confidence(pd.Series({**common, "pa_pm25_hourly_source": "loose_fallback"}), CFG)
    assert loose < strict


if __name__ == "__main__":
    test_classify_alert_level()
    test_apply_binary_hysteresis()
    test_confidence_clipping()
    test_ema_output_length()
    test_dual_ema_columns_and_length()
    test_early_warning_forecasts_non_negative()
    test_hysteresis_does_not_flicker_near_threshold()
    test_loose_confidence_lower_than_strict()
    print("fusion_alert tests passed")
