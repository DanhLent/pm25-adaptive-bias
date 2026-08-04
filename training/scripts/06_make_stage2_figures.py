from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.fusion.alert_logic import load_config


def _finish(ax, title: str, ylabel: str, path: Path) -> None:
    ax.set_title(title)
    ax.set_xlabel("Time")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    handles, _ = ax.get_legend_handles_labels()
    if handles:
        ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d\n%H:%M"))
    ax.figure.autofmt_xdate()
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=160)
    plt.close(ax.figure)


def main() -> None:
    root = Path.cwd()
    cfg = load_config(root / "config.yaml")
    figures_dir = root / cfg["paths"]["figures_dir"]
    figures_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(root / cfg["fusion_alert"]["output_timeline"], parse_dates=["time"])

    fig, ax = plt.subplots(figsize=(11, 4.8))
    for col in ["cams_pm25", "pa_pm25_hourly", "fused_pm25_stage1", "fused_pm25_stage2"]:
        if col in df.columns:
            ax.plot(df["time"], df[col], label=col, linewidth=1.4)
    _finish(ax, "Stage 2 Fusion Timeline", "PM2.5 (ug/m3)", figures_dir / "14_stage2_fusion_timeline.png")

    fig, ax = plt.subplots(figsize=(11, 4.8))
    for col in ["residual_raw", "residual_single_ema", "residual_dual_ema_correction"]:
        ax.plot(df["time"], df[col], label=col, linewidth=1.4)
    _finish(ax, "Stage 2 Residual Filters", "PM2.5 residual/correction (ug/m3)", figures_dir / "15_stage2_residual_filters.png")

    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(df["time"], df["sensor_confidence"], label="sensor_confidence", linewidth=1.5)
    ax.set_ylim(-0.05, 1.05)
    _finish(ax, "Stage 2 Sensor Confidence", "Confidence", figures_dir / "16_stage2_sensor_confidence.png")

    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(df["time"], df["fused_pm25_stage2"], label="fused_pm25_stage2", linewidth=1.5)
    ax.step(df["time"], df["binary_exceed_35_hysteresis"].astype(int) * df["fused_pm25_stage2"].max(), where="post", label="hysteresis state scaled", alpha=0.6)
    ax.axhline(cfg["fusion_alert"]["alert_logic"]["hysteresis_on"], color="red", linestyle="--", label="hysteresis_on")
    ax.axhline(cfg["fusion_alert"]["alert_logic"]["hysteresis_off"], color="orange", linestyle="--", label="hysteresis_off")
    _finish(ax, "Stage 2 Alert Hysteresis", "PM2.5 (ug/m3)", figures_dir / "17_stage2_alert_hysteresis.png")

    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(df["time"], df["fused_pm25_stage2"], label="fused_pm25_stage2", linewidth=2)
    for h in cfg["fusion_alert"]["early_warning"]["horizons_hours"]:
        col = f"forecast_pm25_{h}h_linear"
        if col in df.columns:
            ax.plot(df["time"], df[col], label=col, alpha=0.8)
    ax.axhline(cfg["fusion_alert"]["alert_logic"]["threshold_exceed"], color="red", linestyle="--", label="threshold_exceed")
    _finish(ax, "Stage 2 Early Warning Forecasts", "PM2.5 (ug/m3)", figures_dir / "18_stage2_early_warning_forecasts.png")

    print(f"wrote Stage 2 figures to: {figures_dir}")


if __name__ == "__main__":
    main()
