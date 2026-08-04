from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.loading import load_config
from pm25_alert.evaluation import ALPHA_SHIFTS, evaluate_alpha_candidates


def _evaluation_frame(hours: int = 72) -> pd.DataFrame:
    time = pd.date_range("2026-07-01", periods=hours, freq="h", tz="UTC")
    cams = [20.0 + (index % 6) for index in range(hours)]
    pa = [value + 8.0 for value in cams]
    qc_ok = [0 if index % 7 == 0 else 1 for index in range(hours)]
    return pd.DataFrame(
        {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_local": time.tz_convert("Asia/Ho_Chi_Minh").astype(str),
            "hour": time.tz_convert("Asia/Ho_Chi_Minh").hour,
            "sample_valid": 1,
            "qc_ok": qc_ok,
            "qc_score": qc_ok,
            "source_type": "purpleair_10min",
            "qc_reason_codes": "ok",
            "cams_pm25": cams,
            "pa_pm25_hourly": pa,
        }
    )


def test_alpha_evaluation_is_chronological_and_never_promotes(tmp_path):
    report = evaluate_alpha_candidates(
        _evaluation_frame(),
        config=load_config(ROOT / "config.yaml"),
        output_dir=tmp_path,
        requested_folds=3,
        minimum_valid_hours=16,
    )
    assert report["status"] == "evaluated"
    assert [item["alpha_shift"] for item in report["aggregates"]] == list(ALPHA_SHIFTS)
    assert report["active_alpha_shift_before"] == 3
    assert report["active_alpha_shift_after"] == 3
    assert report["auto_promoted"] is False
    assert report["best_observed_shift"] in ALPHA_SHIFTS
    for shift in ALPHA_SHIFTS:
        folds = report["folds"][str(shift)]
        assert folds
        starts = [fold["test_start_utc"] for fold in folds]
        assert starts == sorted(starts)
        assert all(fold["valid_target_hours"] > 0 for fold in folds)
    saved = json.loads((tmp_path / "latest_alpha_candidate.json").read_text())
    assert saved["config_hash"] == report["config_hash"]
    assert (tmp_path / "latest_alpha_candidate.csv").exists()
    assert (tmp_path / "latest_alpha_candidate.md").exists()


def test_alpha_evaluation_reports_insufficient_data_without_winner(tmp_path):
    report = evaluate_alpha_candidates(
        _evaluation_frame(8),
        config=load_config(ROOT / "config.yaml"),
        output_dir=tmp_path,
        minimum_valid_hours=16,
    )
    assert report["status"] == "insufficient_data"
    assert report["best_observed_shift"] is None
    assert report["aggregates"] == []
    assert report["auto_promoted"] is False
