from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - runtime fallback
    RandomForestRegressor = None
    SimpleImputer = None
    Ridge = None
    Pipeline = None
    StandardScaler = None
    SKLEARN_AVAILABLE = False

from pm25_alert.data.features import add_ema
from pm25_alert.data.loading import find_project_root, infer_purpleair_pm25_columns, load_config


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def _metrics(y_true: pd.Series, y_pred: np.ndarray, threshold: float) -> dict:
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    rmse = math.sqrt(float(np.mean((y_true_arr - y_pred_arr) ** 2)))
    ss_res = float(np.sum((y_true_arr - y_pred_arr) ** 2))
    ss_tot = float(np.sum((y_true_arr - np.mean(y_true_arr)) ** 2))
    true_exceed = y_true_arr > threshold
    pred_exceed = y_pred_arr > threshold
    tp = int(np.sum(true_exceed & pred_exceed))
    tn = int(np.sum(~true_exceed & ~pred_exceed))
    fp = int(np.sum(~true_exceed & pred_exceed))
    fn = int(np.sum(true_exceed & ~pred_exceed))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    out = {
        "MAE": float(np.mean(np.abs(y_true_arr - y_pred_arr))),
        "RMSE": rmse,
        "R2": 1 - ss_res / ss_tot if len(y_true_arr) > 1 and ss_tot > 0 else np.nan,
        "accuracy": (tp + tn) / len(y_true_arr) if len(y_true_arr) else np.nan,
        "precision": precision,
        "recall": recall,
        "F1": f1,
    }
    return out


def _fit_predict_numpy_ridge(x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame, alpha: float = 1.0) -> np.ndarray:
    medians = x_train.median(numeric_only=True).fillna(0)
    x_train_filled = x_train.fillna(medians).to_numpy(dtype=float)
    x_test_filled = x_test.fillna(medians).to_numpy(dtype=float)
    means = x_train_filled.mean(axis=0)
    stds = x_train_filled.std(axis=0)
    stds[stds == 0] = 1.0
    x_train_scaled = (x_train_filled - means) / stds
    x_test_scaled = (x_test_filled - means) / stds
    x_train_design = np.column_stack([np.ones(len(x_train_scaled)), x_train_scaled])
    x_test_design = np.column_stack([np.ones(len(x_test_scaled)), x_test_scaled])
    penalty = np.eye(x_train_design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    weights = np.linalg.pinv(x_train_design.T @ x_train_design + penalty) @ x_train_design.T @ y_train.to_numpy(dtype=float)
    return x_test_design @ weights


def _feature_columns(df: pd.DataFrame) -> list[str]:
    prefixes = ("cams_pm25", "pa_pm25_hourly", "residual", "residual_ema", "fused_pm25", "hour_sin", "hour_cos", "month_sin", "month_cos")
    features = []
    for col in df.columns:
        if col in prefixes or col.startswith(("cams_pm25_", "pa_pm25_hourly_", "fused_pm25_", "residual_")):
            if pd.api.types.is_numeric_dtype(df[col]):
                features.append(col)
    return sorted(set(features))


def _split_time(df: pd.DataFrame, test_fraction: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    n_test = max(1, int(math.ceil(len(df) * test_fraction)))
    n_train = len(df) - n_test
    return df.iloc[:n_train].copy(), df.iloc[n_train:].copy()


def _time_range(df: pd.DataFrame) -> str:
    if df.empty or "time" not in df.columns:
        return "n/a"
    return f"{df['time'].min()} to {df['time'].max()}"


def _raw_ab_channel_names(df: pd.DataFrame) -> tuple[str, str]:
    raw_cols = [col for col in df.columns if not str(col).startswith("pa_") and str(col) != "time"]
    a_cols = [col for col in raw_cols if str(col).strip().lower().endswith(" a")]
    b_cols = [col for col in raw_cols if str(col).strip().lower().endswith(" b")]
    if a_cols and b_cols:
        return a_cols[0], b_cols[0]
    mapping = infer_purpleair_pm25_columns(df)
    return mapping.get("a", "not detected"), mapping.get("b", "not detected")


def _write_stage_1_review(root: Path, config: dict, metrics: pd.DataFrame, warnings: list[str]) -> None:
    paths = config["paths"]
    reports_dir = root / paths["reports_dir"]
    interim_dir = root / paths["interim_data_dir"]
    processed_dir = root / paths["processed_data_dir"]
    cams = pd.read_csv(interim_dir / "cams_standardized.csv", parse_dates=["time"])
    pa_qc = pd.read_csv(interim_dir / "purpleair_qc.csv", parse_dates=["time"])
    pa_hourly = pd.read_csv(interim_dir / "purpleair_hourly.csv", parse_dates=["time"])
    merged = pd.read_csv(processed_dir / "pm25_fused_hourly_dataset.csv", parse_dates=["time"])
    channel_a, channel_b = _raw_ab_channel_names(pa_qc)

    raw_samples = len(pa_qc)
    hourly_loose = int(pa_hourly["pa_pm25_hourly_loose"].notna().sum()) if "pa_pm25_hourly_loose" in pa_hourly.columns else len(pa_hourly)
    hourly_strict = int(pa_hourly["pa_pm25_hourly_strict"].notna().sum()) if "pa_pm25_hourly_strict" in pa_hourly.columns else 0
    fallback_hours = int((pa_hourly.get("pa_pm25_hourly_source", pd.Series(dtype=str)) == "loose_fallback").sum())
    bad_rows = int(pa_qc["pa_qc_bad_flag"].fillna(False).sum()) if "pa_qc_bad_flag" in pa_qc.columns else 0
    bad_hours = int((pa_hourly["pa_bad_samples_per_hour"] > 0).sum()) if "pa_bad_samples_per_hour" in pa_hourly.columns else 0
    disagree_rows = int(pa_qc["channel_disagree"].fillna(False).sum()) if "channel_disagree" in pa_qc.columns else 0
    disagree_pct = disagree_rows / raw_samples * 100 if raw_samples else 0
    abs_mean = pa_qc["pa_abs_diff_ab"].mean() if "pa_abs_diff_ab" in pa_qc.columns else float("nan")
    rel_mean = pa_qc["pa_rel_diff_ab"].mean() if "pa_rel_diff_ab" in pa_qc.columns else float("nan")
    zero_positive_note = any("zero positive exceedance samples" in warning for warning in warnings)

    best_lines = []
    if not metrics.empty:
        for h, group in metrics.groupby("horizon_hours"):
            best = group.sort_values("MAE").iloc[0]
            best_lines.append(f"- {h}h best MAE: `{best['model']}` with MAE={best['MAE']:.3f}")

    lines = [
        "# Stage 1 Review",
        "",
        "## Executive Answer",
        "",
        "The Stage 1 pipeline is ready to be frozen as a proof-of-concept data-processing and fusion pipeline. It is not yet a reliable trained forecasting model because only about 49 overlapping hourly CAMS + PurpleAir rows are available and PurpleAir A/B channel disagreement is severe.",
        "",
        "## Files Used",
        "",
        "- CAMS/Open-Meteo: `open-meteo-10.90N106.80E21m.csv`",
        "- PurpleAir: `raw-pm25-gm.csv`",
        "",
        "## Time Ranges",
        "",
        f"- CAMS/Open-Meteo range: {_time_range(cams)}",
        f"- PurpleAir raw range: {_time_range(pa_qc)}",
        f"- PurpleAir hourly range: {_time_range(pa_hourly)}",
        f"- Merged overlap range: {_time_range(merged)}",
        "",
        "## PurpleAir Sample Counts",
        "",
        f"- Raw PurpleAir samples: {raw_samples}",
        f"- Hourly PurpleAir rows before strict QC: {len(pa_hourly)}",
        f"- Hourly PurpleAir rows with loose signal: {hourly_loose}",
        f"- Hourly PurpleAir rows remaining after strict QC/min-sample policy: {hourly_strict}",
        f"- Merged CAMS + PurpleAir rows available: {len(merged)}",
        "",
        "## PurpleAir Channels",
        "",
        f"- Channel A used: `{channel_a}`",
        f"- Channel B used: `{channel_b}`",
        f"- A/B disagreement rows: {disagree_rows} of {raw_samples} ({disagree_pct:.2f}%)",
        f"- Mean absolute A/B difference: {abs_mean:.3f} ug/m3",
        f"- Mean relative A/B difference: {rel_mean:.3f}",
        "",
        "## QC Impact",
        "",
        f"- Raw rows affected by QC problems: {bad_rows} of {raw_samples}",
        f"- Hourly rows containing at least one bad sample: {bad_hours} of {len(pa_hourly)}",
        f"- Hours where strict signal was unavailable and loose fallback was used: {fallback_hours}",
        "- This is a major limitation. Channel disagreement should be investigated before trusting PurpleAir as a correction signal.",
        "",
        "## Resampling and Fusion",
        "",
        f"- PurpleAir was resampled to hourly using `{config['preprocessing']['purpleair_resample_rule']}`.",
        "- `pa_pm25_hourly_loose` uses all non-missing, non-negative, non-extreme samples, including channel-disagree samples.",
        "- `pa_pm25_hourly_strict` excludes rows flagged as `pa_qc_bad_flag`; hours below the configured minimum valid sample count are marked missing.",
        "- `pa_pm25_hourly` uses strict hourly PM2.5 when available, otherwise documented loose fallback.",
        "- `residual = pa_pm25_hourly - cams_pm25`.",
        f"- `residual_ema` uses EMA alpha `{config['preprocessing']['residual_ema_alpha']}`.",
        "- `fused_pm25 = cams_pm25 + residual_ema`.",
        "",
        "## Model Metrics",
        "",
        *(best_lines or ["- No baseline metrics were produced."]),
        "",
        "The model metrics are not meaningful as strong forecasting evidence right now. The test sets contain only 11-12 samples, and the current overlap is too short for robust ML evaluation.",
        "",
        "Classification accuracy may be misleading because the threshold exceedance test set has zero positive exceedance samples. In that situation, a model can get accuracy near 1.0 by predicting no exceedance, while precision, recall, and F1 remain uninformative.",
        "",
        "## Stage 2 Readiness",
        "",
        "Stage 2 is recommended only as a cautious next research/planning stage, not as a claim of reliable ML performance. Stage 2 should focus on longer PurpleAir data collection, channel calibration/QC investigation, robust validation design, and low-complexity hardware-friendly fusion logic before adding more advanced models.",
        "",
        "## Warnings",
        "",
        "- Threshold classification metrics are not meaningful because the test set contains zero positive exceedance samples." if zero_positive_note else "- No zero-positive classification warning was triggered.",
        "- Do not overclaim forecasting performance from the current 49-hour overlap.",
    ]
    (reports_dir / "STAGE_1_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = find_project_root()
    config = load_config(root / "config.yaml")
    paths = config["paths"]
    processed_path = root / paths["processed_data_dir"] / "pm25_fused_hourly_dataset.csv"
    metrics_dir = root / paths["metrics_dir"]
    predictions_dir = root / paths["predictions_dir"]
    reports_dir = root / paths["reports_dir"]
    for directory in (metrics_dir, predictions_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(processed_path, parse_dates=["time"])
    df = df.sort_values("time").reset_index(drop=True)
    features = _feature_columns(df)
    rows = []
    prediction_frames = []
    threshold = float(config["alert_thresholds"]["moderate"])
    test_fraction = float(config["forecasting"]["test_fraction"])
    warnings = []

    for h in config["forecasting"]["horizons_hours"]:
        target = f"target_pm25_{h}h"
        usable = df.dropna(subset=[target]).copy()
        if len(usable) < 4:
            warnings.append(f"Horizon {h}h has only {len(usable)} usable samples; ML models were skipped.")
            continue
        train, test = _split_time(usable, test_fraction)
        if len(train) < 3 or len(test) < 1:
            warnings.append(f"Horizon {h}h has train={len(train)}, test={len(test)}; ML metrics are not reliable.")
        positive_test_samples = int((test[target] > threshold).sum())
        if positive_test_samples == 0:
            warnings.append(f"Horizon {h}h threshold classification metrics are not meaningful because the test set contains zero positive exceedance samples.")

        base_col = "fused_pm25" if "fused_pm25" in test.columns else "cams_pm25"
        model_predictions: dict[str, np.ndarray] = {
            "persistence": test[base_col].to_numpy(),
        }
        ema_train_test = add_ema(usable[base_col], float(config["preprocessing"]["residual_ema_alpha"]))
        model_predictions["ema"] = ema_train_test.loc[test.index].to_numpy()

        if len(train) >= 8 and len(features) > 0:
            x_train, y_train = train[features], train[target]
            x_test = test[features]
            if SKLEARN_AVAILABLE:
                ridge = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))])
                rf = Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("model", RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=42)),
                    ]
                )
                for name, model in {"ridge": ridge, "random_forest": rf}.items():
                    model.fit(x_train, y_train)
                    model_predictions[name] = model.predict(x_test)
            else:
                model_predictions["ridge"] = _fit_predict_numpy_ridge(x_train, y_train, x_test)
                warnings.append("scikit-learn is not installed in this runtime; RandomForestRegressor was skipped. Install requirements.txt to enable it.")
        else:
            warnings.append(f"Horizon {h}h has only {len(train)} training samples; Ridge/RandomForest skipped.")

        for model_name, y_pred in model_predictions.items():
            metric_row = {
                "horizon_hours": h,
                "model": model_name,
                "train_samples": len(train),
                "test_samples": len(test),
                "positive_test_samples": positive_test_samples,
                **_metrics(test[target], y_pred, threshold),
            }
            rows.append(metric_row)
            pred = test[["time", target]].copy()
            pred["horizon_hours"] = h
            pred["model"] = model_name
            pred["prediction_pm25"] = y_pred
            pred = pred.rename(columns={target: "actual_pm25"})
            prediction_frames.append(pred)

    metrics = pd.DataFrame(rows)
    predictions = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame()
    metrics.to_csv(metrics_dir / "baseline_metrics.csv", index=False)
    predictions.to_csv(predictions_dir / "predictions_baseline.csv", index=False)

    best_lines = []
    if not metrics.empty:
        for h, group in metrics.groupby("horizon_hours"):
            best = group.sort_values("MAE").iloc[0]
            best_lines.append(f"- {h}h: `{best['model']}` with MAE={best['MAE']:.3f}")
    short_warning = len(df) < 24 * 14
    if short_warning:
        warnings.append("The current PurpleAir/CAMS overlap is short; results are useful for pipeline validation, not strong ML claims.")

    warning_lines = [f"- {warning}" for warning in sorted(set(warnings))] if warnings else ["- None."]
    lines = [
        "# Model Report",
        "",
        f"- Dataset rows: {len(df)}",
        f"- Selected features ({len(features)}): {', '.join(f'`{f}`' for f in features)}",
        "",
        "## Best Model by MAE",
        "",
        *(best_lines or ["- No model metrics were produced."]),
        "",
        "## Metrics",
        "",
        _markdown_table([str(col) for col in metrics.columns], metrics.round(4).astype(str).values.tolist()) if not metrics.empty else "No metrics available.",
        "",
        "## Trust and Limitations",
        "",
        "Current results should not be overclaimed. They are based on a time-based split, but the short overlap limits statistical reliability.",
        "Threshold classification metrics are not meaningful when the test set contains zero positive exceedance samples; high accuracy can simply mean the model predicted the majority no-exceedance class.",
        "",
        "## Warnings",
        "",
        *warning_lines,
    ]
    (reports_dir / "model_report.md").write_text("\n".join(lines), encoding="utf-8")
    _write_stage_1_review(root, config, metrics, warnings)
    print(f"Wrote {metrics_dir / 'baseline_metrics.csv'}")


if __name__ == "__main__":
    main()
