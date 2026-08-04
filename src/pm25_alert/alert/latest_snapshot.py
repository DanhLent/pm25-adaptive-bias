from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pm25_alert.data.canonical import write_csv_atomic
from pm25_alert.data.loading import find_project_root, load_config
from pm25_alert.state import write_json_atomic


def _json_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def make_latest_snapshot(timeline_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(timeline_path)
    if df.empty:
        raise ValueError(f"Timeline is empty; cannot create latest snapshot: {timeline_path}")
    time_column = "timestamp_utc" if "timestamp_utc" in df.columns else "time"
    df[time_column] = pd.to_datetime(df[time_column], errors="coerce", utc=True)
    df = df.dropna(subset=[time_column]).sort_values(time_column)
    latest = df.tail(1).copy()
    hardware_aligned = "fused_pm25_x16" in latest.columns
    snapshot_name = (
        "latest_hardware_aligned_snapshot.csv"
        if hardware_aligned
        else "latest_fusion_alert_snapshot.csv"
    )
    write_csv_atomic(latest, output_dir / snapshot_name)
    row = latest.iloc[0]

    def get(col: str):
        return _json_value(row[col]) if col in row.index else None

    summary = {
        "pipeline": (
            "hardware_aligned_core_v1"
            if hardware_aligned
            else "dual_ema_reference"
        ),
        "latest_time": str(get(time_column)),
        "latest_cams_pm25": get("cams_pm25"),
        "latest_pa_pm25_hourly": (
            get("purpleair_pm25")
            if hardware_aligned
            else get("pa_pm25_hourly")
        ),
        "latest_fused_pm25": (
            get("fused_pm25")
            if hardware_aligned
            else get("fused_pm25_stage2")
        ),
        "latest_fused_pm25_x16": get("fused_pm25_x16"),
        "latest_bias_x16": get("bias_after_x16"),
        "latest_qc_ok": get("qc_ok"),
        "latest_qc_score": get("qc_score"),
        "latest_alert_level": (
            get("alert_level")
            if hardware_aligned
            else get("alert_level_stage2_now")
        ),
        "latest_alert_state": (
            get("alert_state_after")
            if hardware_aligned
            else get("binary_exceed_35_hysteresis")
        ),
        "latest_fused_pm25_stage2": get("fused_pm25_stage2"),
        "latest_sensor_confidence": get("sensor_confidence"),
        "latest_alert_level_stage2_now": get("alert_level_stage2_now"),
        "latest_binary_exceed_35_hysteresis": get("binary_exceed_35_hysteresis"),
        "pred_will_exceed_35_1h": get("pred_will_exceed_35_1h"),
        "pred_will_exceed_35_3h": get("pred_will_exceed_35_3h"),
        "pred_will_exceed_35_6h": get("pred_will_exceed_35_6h"),
        "warning": "diagnostic/proof-of-concept only",
    }
    write_json_atomic(output_dir / "latest_alert_summary.json", summary)
    return summary


def main() -> None:
    root = find_project_root()
    cfg = load_config(root / "config.yaml")
    timeline_path = root / cfg["hardware_aligned"]["trace_csv"]
    output_dir = root / cfg["hardware_aligned"]["latest_output_dir"]
    summary = make_latest_snapshot(timeline_path, output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
