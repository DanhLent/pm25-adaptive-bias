from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.alert import latest_snapshot


def _load_snapshot_module():
    return latest_snapshot


def test_latest_snapshot_json_from_fake_timeline():
    module = _load_snapshot_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        timeline = tmp_path / "timeline.csv"
        out_dir = tmp_path / "latest"
        pd.DataFrame(
            {
                "time": ["2026-05-14 09:00:00+07:00", "2026-05-14 10:00:00+07:00"],
                "cams_pm25": [10.0, 11.0],
                "pa_pm25_hourly": [9.0, 10.5],
                "fused_pm25_stage2": [9.5, 10.8],
                "sensor_confidence": [0.2, 0.3],
                "alert_level_stage2_now": ["good", "good"],
                "binary_exceed_35_hysteresis": [False, False],
                "pred_will_exceed_35_1h": [False, False],
                "pred_will_exceed_35_3h": [False, False],
                "pred_will_exceed_35_6h": [False, False],
            }
        ).to_csv(timeline, index=False)
        summary = module.make_latest_snapshot(timeline, out_dir)
        saved = json.loads((out_dir / "latest_alert_summary.json").read_text(encoding="utf-8"))
        assert summary["latest_cams_pm25"] == 11.0
        assert saved["warning"] == "diagnostic/proof-of-concept only"
        assert (out_dir / "latest_fusion_alert_snapshot.csv").exists()


if __name__ == "__main__":
    test_latest_snapshot_json_from_fake_timeline()
    print("latest_snapshot tests passed")
