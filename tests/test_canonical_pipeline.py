from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "purpleair_semicolon_decimal_comma.csv"
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.canonical import (
    PURPLEAIR_10MIN_COLUMNS,
    append_canonical_atomic,
    build_hourly_from_canonical,
    merge_hourly_sources,
    normalize_manual_purpleair_csv,
)
from pm25_alert.data.loading import load_config, read_csv_smart
from pm25_alert.data.qc import aggregate_purpleair_hourly, qc_purpleair_samples


def _load_collector_module():
    path = ROOT / "tools" / "data_collection" / "purpleair_collector.py"
    spec = importlib.util.spec_from_file_location("purpleair_collector_phase1", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_supplied_semicolon_decimal_comma_csv_imports_correctly():
    path = FIXTURE
    frame = read_csv_smart(path)
    assert frame.shape == (8, 4)
    assert list(frame.columns) == ["DateTime", "Average", "VNU-HCM A", "VNU-HCM B"]
    assert frame["Average"].notna().sum() == 2
    assert frame["VNU-HCM A"].notna().sum() == 8
    assert frame["VNU-HCM B"].notna().sum() == 8
    assert pd.api.types.is_numeric_dtype(frame["VNU-HCM A"])


def test_manual_import_uses_ab_not_sparse_average():
    cfg = load_config(ROOT / "config.yaml")
    frame = normalize_manual_purpleair_csv(
        FIXTURE,
        sensor_index=9520,
        timezone_name=cfg["project"]["timezone"],
    )
    assert len(frame) == 8
    assert frame["pm25_cf_1"].notna().sum() == 0
    assert frame["pm25_cf_1_a"].notna().sum() == 8
    assert frame["pm25_cf_1_b"].notna().sum() == 8
    expected = (frame.loc[0, "pm25_cf_1_a"] + frame.loc[0, "pm25_cf_1_b"]) / 2
    assert frame.loc[0, "pm25"] == expected
    assert frame["timestamp"].str.endswith("Z").all()


def test_required_ab_and_rule_and_single_channel_reasons():
    cfg = load_config(ROOT / "config.yaml")
    samples = pd.DataFrame(
        {
            "time": pd.date_range("2026-07-01", periods=4, freq="10min", tz="UTC"),
            "pa_pm25_a_raw": [2.9, 7.27, 5.0, None],
            "pa_pm25_b_raw": [1.6, 33.27, None, None],
        }
    )
    qc = qc_purpleair_samples(samples, cfg)
    assert not bool(qc.loc[0, "channel_disagree"])
    assert bool(qc.loc[1, "channel_disagree"])
    assert bool(qc.loc[2, "pa_single_channel_flag"])
    assert qc.loc[2, "qc_score"] == cfg["purpleair_qc_policy"]["single_channel_qc_score"]
    assert "single_channel_fallback" in qc.loc[2, "qc_reason_codes"]
    assert bool(qc.loc[3, "pa_hard_invalid_flag"])
    assert "no_usable_value" in qc.loc[3, "qc_reason_codes"]



def test_out_of_range_companion_channel_is_non_strict_fallback_not_total_loss():
    cfg = load_config(ROOT / "config.yaml")
    samples = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-07-01T00:00:00Z"]),
            "pa_pm25_a_raw": [10.0],
            "pa_pm25_b_raw": [2000.0],
        }
    )

    qc = qc_purpleair_samples(samples, cfg)

    assert qc.loc[0, "pa_pm25_qc"] == 10.0
    assert bool(qc.loc[0, "pa_single_channel_flag"])
    assert not bool(qc.loc[0, "pa_hard_invalid_flag"])
    assert bool(qc.loc[0, "pa_qc_bad_flag"])
    assert not bool(qc.loc[0, "pa_sample_good"])
    assert "out_of_range" in qc.loc[0, "qc_reason_codes"]
    assert "single_channel_fallback" in qc.loc[0, "qc_reason_codes"]


def test_merge_hourly_sources_handles_all_na_schema_without_future_warning():
    ten = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-07-01T00:00:00Z"]),
            "pa_pm25_hourly": [10.0],
            "pa_pm25_hourly_strict": [10.0],
            "legacy_only": [pd.NA],
        }
    )
    legacy = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-07-01T01:00:00Z"]),
            "pa_pm25_hourly": [20.0],
            "pa_pm25_hourly_strict": [pd.NA],
            "legacy_only": ["legacy"],
        }
    )

    merged = merge_hourly_sources(ten, legacy)

    assert len(merged) == 2
    assert list(merged["legacy_only"].dropna()) == ["legacy"]

def test_four_good_samples_with_coverage_make_strict_hour():
    cfg = load_config(ROOT / "config.yaml")
    samples = pd.DataFrame(
        {
            "time": pd.date_range("2026-07-01", periods=6, freq="10min", tz="UTC"),
            "pa_pm25_a_raw": [10.0, 11.0, 12.0, 13.0, 7.27, None],
            "pa_pm25_b_raw": [10.2, 11.2, 12.2, 13.2, 33.27, None],
        }
    )
    qc = qc_purpleair_samples(samples, cfg)
    hourly = aggregate_purpleair_hourly(qc, cfg)
    assert len(hourly) == 1
    assert hourly.loc[0, "pa_good_samples_per_hour"] == 4
    assert hourly.loc[0, "pa_severe_disagree_count"] == 1
    assert hourly.loc[0, "qc_ok"] == 1
    assert hourly.loc[0, "pa_pm25_hourly"] == 11.6


def test_legacy_hourly_never_double_counts_a_ten_minute_hour():
    ten = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-07-01T00:00:00Z"]),
            "pa_pm25_hourly": [10.0],
            "source_type": ["purpleair_10min"],
            "qc_ok": [1],
        }
    )
    legacy = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2026-07-01T00:00:00Z", "2026-07-01T01:00:00Z"]
            ),
            "pa_pm25_hourly": [99.0, 20.0],
            "source_type": ["purpleair_legacy_hourly"] * 2,
            "qc_ok": [0, 0],
        }
    )
    merged = merge_hourly_sources(ten, legacy)
    assert len(merged) == 2
    assert merged.loc[merged["time"] == pd.Timestamp("2026-07-01T00:00:00Z"), "pa_pm25_hourly"].iloc[0] == 10.0
    assert merged["time"].duplicated().sum() == 0


def test_collector_incremental_window_uses_last_timestamp_minus_overlap(tmp_path):
    module = _load_collector_module()
    canonical = tmp_path / "purpleair_10min.csv"
    pd.DataFrame(
        {
            "timestamp": ["2026-07-30T10:00:00Z"],
            "time": ["2026-07-30T10:00:00Z"],
        }
    ).to_csv(canonical, index=False)
    config = {
        "incremental_overlap_hours": 2,
        "initial_lookback_hours": 72,
        "reconciliation_hours": 72,
    }
    start, end, mode = module.select_history_window(
        config,
        canonical,
        now=datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc),
    )
    assert mode == "incremental"
    assert start == datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def test_header_only_canonical_append_preserves_rows_and_numeric_dtype(tmp_path):
    cfg = load_config(ROOT / "config.yaml")
    path = tmp_path / "purpleair_10min.csv"
    pd.DataFrame(columns=PURPLEAIR_10MIN_COLUMNS).to_csv(path, index=False)
    batch = normalize_manual_purpleair_csv(
        FIXTURE,
        sensor_index=9520,
        timezone_name=cfg["project"]["timezone"],
    ).iloc[:1]

    canonical, duplicates = append_canonical_atomic(path, batch)

    assert duplicates == 0
    assert len(canonical) == 1
    assert pd.api.types.is_numeric_dtype(canonical["pm25_cf_1_a"])
