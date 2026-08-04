from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.loading import find_project_root, load_config


def _finish(ax, title: str, ylabel: str, path: Path) -> None:
    ax.set_title(title)
    ax.set_xlabel("Time")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    if ax.get_legend_handles_labels()[0]:
        ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d\n%H:%M"))
    ax.figure.autofmt_xdate()
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=160)
    plt.close(ax.figure)


def _plot_series(df: pd.DataFrame, ycols: list[str], title: str, ylabel: str, path: Path) -> None:
    if df.empty or not any(col in df.columns for col in ycols):
        return
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for col in ycols:
        if col in df.columns:
            ax.plot(df["time"], df[col], label=col, linewidth=1.4)
    _finish(ax, title, ylabel, path)


def main() -> None:
    root = find_project_root()
    config = load_config(root / "config.yaml")
    paths = config["paths"]
    figures_dir = root / paths["figures_dir"]
    figures_dir.mkdir(parents=True, exist_ok=True)

    interim = root / paths["interim_data_dir"]
    processed = root / paths["processed_data_dir"]
    predictions_dir = root / paths["predictions_dir"]

    cams = pd.read_csv(interim / "cams_standardized.csv", parse_dates=["time"])
    pa_qc = pd.read_csv(interim / "purpleair_qc.csv", parse_dates=["time"])
    pa_hourly = pd.read_csv(interim / "purpleair_hourly.csv", parse_dates=["time"])
    merged = pd.read_csv(processed / "pm25_fused_hourly_dataset.csv", parse_dates=["time"])

    _plot_series(cams, ["cams_pm25"], "CAMS/Open-Meteo PM2.5 Full Time Series", "PM2.5 (ug/m3)", figures_dir / "01_cams_pm25_full_timeseries.png")
    _plot_series(pa_qc, ["pa_pm25_qc"], "PurpleAir Raw/QC PM2.5 Time Series", "PM2.5 (ug/m3)", figures_dir / "02_purpleair_raw_pm25_timeseries.png")
    _plot_series(pa_qc, ["pa_pm25_a", "pa_pm25_b"], "PurpleAir A/B Channel Comparison", "PM2.5 (ug/m3)", figures_dir / "03_purpleair_ab_channel_comparison.png")
    _plot_series(pa_hourly, ["pa_pm25_hourly"], "PurpleAir Hourly PM2.5", "PM2.5 (ug/m3)", figures_dir / "04_purpleair_hourly_pm25.png")
    _plot_series(merged, ["cams_pm25", "pa_pm25_hourly"], "CAMS vs PurpleAir Overlap", "PM2.5 (ug/m3)", figures_dir / "05_cams_vs_purpleair_overlap.png")
    _plot_series(merged, ["residual"], "PurpleAir Minus CAMS Residual", "PM2.5 (ug/m3)", figures_dir / "06_residual_over_time.png")
    _plot_series(merged, ["residual_ema"], "Residual EMA Over Time", "PM2.5 (ug/m3)", figures_dir / "07_residual_ema_over_time.png")
    _plot_series(merged, ["fused_pm25", "cams_pm25", "pa_pm25_hourly"], "Fused PM2.5 vs CAMS vs PurpleAir", "PM2.5 (ug/m3)", figures_dir / "08_fused_vs_cams_vs_purpleair.png")
    _plot_series(pa_qc, ["pa_abs_diff_ab"], "PurpleAir A/B Absolute Difference", "PM2.5 (ug/m3)", figures_dir / "11_purpleair_ab_difference.png")
    _plot_series(pa_hourly, ["pa_bad_fraction_per_hour"], "PurpleAir Bad Sample Fraction by Hour", "Fraction", figures_dir / "12_purpleair_bad_fraction_hourly.png")
    _plot_series(
        pa_hourly,
        ["pa_pm25_hourly_loose", "pa_pm25_hourly_strict", "pa_pm25_hourly"],
        "Loose vs Strict PurpleAir Hourly PM2.5",
        "PM2.5 (ug/m3)",
        figures_dir / "13_loose_vs_strict_purpleair_hourly.png",
    )

    if "alert_level_now" in merged.columns and not merged.empty:
        levels = ["missing", "good", "moderate", "unhealthy_sensitive", "unhealthy", "very_unhealthy"]
        level_map = {level: i for i, level in enumerate(levels)}
        fig, ax = plt.subplots(figsize=(11, 3.8))
        ax.step(merged["time"], merged["alert_level_now"].map(level_map), where="post", label="alert_level_now")
        ax.set_yticks(range(len(levels)))
        ax.set_yticklabels(levels)
        _finish(ax, "Alert Level Timeline", "Alert level", figures_dir / "09_alert_level_timeline.png")

    pred_path = predictions_dir / "predictions_baseline.csv"
    if pred_path.exists():
        preds = pd.read_csv(pred_path, parse_dates=["time"])
        for h in sorted(preds["horizon_hours"].dropna().unique()):
            subset = preds[preds["horizon_hours"] == h]
            fig, ax = plt.subplots(figsize=(11, 4.5))
            actual = subset.drop_duplicates("time").sort_values("time")
            ax.plot(actual["time"], actual["actual_pm25"], label="actual", linewidth=2)
            for model, group in subset.groupby("model"):
                group = group.sort_values("time")
                ax.plot(group["time"], group["prediction_pm25"], label=model, alpha=0.8)
            _finish(ax, f"Prediction vs Actual ({int(h)}h Horizon)", "PM2.5 (ug/m3)", figures_dir / f"10_prediction_vs_actual_{int(h)}h.png")

    print(f"Wrote figures to {figures_dir}")


if __name__ == "__main__":
    main()
