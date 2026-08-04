from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.fusion.alert_logic import load_config


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "No metrics available."
    rounded = df.round(4).astype(str)
    header = "| " + " | ".join(rounded.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(rounded.columns)) + " |"
    rows = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rounded.values.tolist()]
    return "\n".join([header, sep, *rows])


def _binary_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    true = y_true.astype(bool).to_numpy()
    pred = y_pred.astype(bool).to_numpy()
    tp = int(np.sum(true & pred))
    tn = int(np.sum(~true & ~pred))
    fp = int(np.sum(~true & pred))
    fn = int(np.sum(true & ~pred))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "accuracy": (tp + tn) / len(true) if len(true) else np.nan,
        "precision": precision,
        "recall": recall,
        "F1": f1,
        "positive_support": int(np.sum(true)),
        "negative_support": int(np.sum(~true)),
    }


def _to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def _write_report(path: Path, metrics: pd.DataFrame, timeline: pd.DataFrame) -> None:
    warnings = sorted(set(metrics["metric_warning"].dropna())) if "metric_warning" in metrics.columns else []
    warning_lines = [f"- {warning}" for warning in warnings] if warnings else ["- None."]
    has_zero_positive = bool(
        ((metrics["metric_type"] == "classification") & (metrics["positive_support"].fillna(0) == 0)).any()
    ) if not metrics.empty else False
    best_lines = []
    reg = metrics[metrics["metric_type"] == "regression"]
    if not reg.empty:
        for _, row in reg.iterrows():
            best_lines.append(f"- {int(row['horizon_hours'])}h linear projection: MAE={row['MAE']:.3f}, RMSE={row['RMSE']:.3f}")
    lines = [
        "# Stage 2 Evaluation",
        "",
        "## Critical Warning",
        "",
        (
            "**Classification accuracy is not meaningful in this run because every evaluated horizon has zero positive exceedance samples. "
            "Accuracy mostly measures the dominant no-exceedance class, not useful warning skill.**"
            if has_zero_positive
            else "Classification metrics include at least one positive exceedance sample."
        ),
        "",
        "These metrics are diagnostic only. The CAMS + PurpleAir overlap contains 49 hourly rows, so this is not a reliable operational validation.",
        "",
        f"- Timeline rows: {len(timeline)}",
        f"- Mean sensor confidence: {timeline['sensor_confidence'].mean():.4f}",
        f"- Hysteresis alert-on hours: {int(timeline['binary_exceed_35_hysteresis'].sum())}",
        "",
        "## Regression Diagnostics",
        "",
        *(best_lines or ["- No regression metrics available."]),
        "",
        "## Classification Warnings",
        "",
        *warning_lines,
        "",
        "## Full Metrics",
        "",
        _markdown_table(metrics),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = Path.cwd()
    cfg = load_config(root / "config.yaml")
    timeline_path = root / cfg["fusion_alert"]["output_timeline"]
    metrics_path = root / cfg["fusion_alert"]["output_metrics"]
    report_path = root / cfg["paths"]["reports_dir"] / "STAGE_2_EVALUATION.md"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(timeline_path, parse_dates=["time"])
    rows = []
    for h in cfg["fusion_alert"]["early_warning"]["horizons_hours"]:
        forecast = f"forecast_pm25_{h}h_linear"
        target = f"target_pm25_{h}h"
        pred_flag = f"pred_will_exceed_35_{h}h"
        true_flag = f"will_exceed_35_{h}h"
        if forecast in df.columns and target in df.columns:
            subset = df.dropna(subset=[forecast, target])
            if not subset.empty:
                err = subset[forecast] - subset[target]
                rows.append(
                    {
                        "horizon_hours": h,
                        "metric_type": "regression",
                        "n_samples": len(subset),
                        "MAE": float(err.abs().mean()),
                        "RMSE": float(np.sqrt(np.mean(err**2))),
                        "accuracy": np.nan,
                        "precision": np.nan,
                        "recall": np.nan,
                        "F1": np.nan,
                        "positive_support": np.nan,
                        "negative_support": np.nan,
                        "is_metric_meaningful": False,
                        "metric_warning": "Diagnostic only; overlap is too short for reliable forecasting claims.",
                    }
                )
        if pred_flag in df.columns and true_flag in df.columns:
            subset = df.dropna(subset=[pred_flag, true_flag])
            if not subset.empty:
                y_true = _to_bool(subset[true_flag])
                y_pred = _to_bool(subset[pred_flag])
                binary = _binary_metrics(y_true, y_pred)
                warning = ""
                is_meaningful = True
                if binary["positive_support"] == 0:
                    warning = "No positive exceedance samples; classification metrics are not meaningful."
                    is_meaningful = False
                rows.append(
                    {
                        "horizon_hours": h,
                        "metric_type": "classification",
                        "n_samples": len(subset),
                        "MAE": np.nan,
                        "RMSE": np.nan,
                        **binary,
                        "is_metric_meaningful": is_meaningful,
                        "metric_warning": warning,
                    }
                )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(metrics_path, index=False)
    _write_report(report_path, metrics, df)
    print(f"wrote: {metrics_path}")
    print(f"wrote: {report_path}")


if __name__ == "__main__":
    main()
