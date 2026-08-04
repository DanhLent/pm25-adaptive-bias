from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.hardware import process_hardware_timeline, run_hardware_rows
from pm25_alert.data.loading import load_config


def _timeline() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range(
                "2026-07-01", periods=8, freq="h", tz="UTC"
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_local": pd.date_range(
                "2026-07-01 07:00", periods=8, freq="h", tz="Asia/Ho_Chi_Minh"
            ).astype(str),
            "hour": list(range(7, 15)),
            "sample_valid": [1] * 8,
            "qc_ok": [1, 1, 0, 1, 0, 1, 1, 0],
            "qc_score": [1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0],
            "source_type": [
                "purpleair_10min",
                "purpleair_10min",
                "purpleair_missing",
                "purpleair_10min",
                "purpleair_legacy_hourly",
                "purpleair_10min",
                "purpleair_10min",
                "purpleair_missing",
            ],
            "qc_reason_codes": ["ok"] * 8,
            "cams_pm25": [10.0] * 8,
            "pa_pm25_hourly": [18.0, 18.0, None, 18.0, 40.0, 18.0, 18.0, None],
        }
    )


def test_missing_or_qc_failed_purpleair_holds_bias_but_emits_fused():
    frame = _timeline().iloc[:3]
    trace, _ = run_hardware_rows(
        frame,
        alpha_shift=3,
        model_version="test",
        config_hash="test",
    )
    assert trace.loc[2, "qc_ok"] == 0
    assert trace.loc[2, "accepted"] == 0
    assert trace.loc[2, "bias_after_x16"] == trace.loc[2, "bias_before_x16"]
    assert trace.loc[2, "fused_pm25_x16"] == (
        trace.loc[2, "cams_pm25_x16"] + trace.loc[2, "bias_before_x16"]
    )


def test_one_shot_and_split_run_are_bit_identical():
    frame = _timeline()
    one_shot, one_state = run_hardware_rows(
        frame,
        alpha_shift=3,
        model_version="test",
        config_hash="hash",
    )
    first, first_state = run_hardware_rows(
        frame.iloc[:3],
        alpha_shift=3,
        model_version="test",
        config_hash="hash",
    )
    second, second_state = run_hardware_rows(
        frame.iloc[3:],
        alpha_shift=3,
        model_version="test",
        config_hash="hash",
        initial_state=first_state,
    )
    split = pd.concat([first, second], ignore_index=True)
    pd.testing.assert_frame_equal(one_shot, split)
    assert one_state == second_state


def test_persistent_incremental_and_reconciliation_replay(tmp_path):
    config = load_config(ROOT / "config.yaml")
    trace_path = tmp_path / "trace.csv"
    state_path = tmp_path / "state.json"
    frame = _timeline()

    first = process_hardware_timeline(
        frame.iloc[:6],
        config=config,
        trace_path=trace_path,
        state_path=state_path,
    )
    assert first["mode"] == "full_replay"
    original = pd.read_csv(trace_path)

    repeated = process_hardware_timeline(
        frame.iloc[:6],
        config=config,
        trace_path=trace_path,
        state_path=state_path,
    )
    assert repeated["mode"] == "incremental"
    assert repeated["rows_processed"] == 0
    pd.testing.assert_frame_equal(original, pd.read_csv(trace_path))

    extended = process_hardware_timeline(
        frame,
        config=config,
        trace_path=trace_path,
        state_path=state_path,
    )
    assert extended["mode"] == "incremental"
    assert extended["rows_processed"] == 2
    assert len(pd.read_csv(trace_path)) == 8

    reconciled = frame.copy()
    reconciled.loc[1, "pa_pm25_hourly"] = 50.0
    replayed = process_hardware_timeline(
        reconciled,
        config=config,
        trace_path=trace_path,
        state_path=state_path,
    )
    assert replayed["mode"] == "full_replay"
    assert replayed["replay_reason"] == "historical_input_changed_or_trace_missing"
    after = pd.read_csv(trace_path)
    assert len(after) == 8
    assert after.loc[2, "bias_before_x16"] != original.loc[2, "bias_before_x16"]
