from __future__ import annotations

import json
import math
import os
import statistics
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from pm25_alert.data.canonical import write_csv_atomic
from pm25_alert.hardware import input_fingerprint, normalize_hourly_input, run_hardware_rows
from pm25_alert.state import processing_config_hash, write_json_atomic
from python_model.fixed_point.pm25_core_v1_fixed import (
    ACTIVE_CONFIG,
    BIAS_MAX_X16,
    BIAS_MIN_X16,
    PM25_MAX_X16,
    PM25_MIN_X16,
)


ALPHA_SHIFTS = (2, 3, 4, 5, 6)


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        suffix=".tmp",
        prefix=f"{path.name}.",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def _metric(errors: list[float]) -> tuple[float | None, float | None]:
    if not errors:
        return None, None
    return (
        statistics.fmean(abs(value) for value in errors),
        math.sqrt(statistics.fmean(value * value for value in errors)),
    )


def _folds(valid_rows: pd.DataFrame, requested_folds: int) -> tuple[int, list[pd.DataFrame]]:
    valid_count = len(valid_rows)
    warmup_count = max(8, valid_count // 4)
    remaining = valid_rows.iloc[warmup_count:]
    if len(remaining) < 8:
        return warmup_count, []
    fold_count = min(requested_folds, max(1, len(remaining) // 8))
    fold_sizes = [len(remaining) // fold_count] * fold_count
    for index in range(len(remaining) % fold_count):
        fold_sizes[index] += 1
    folds = []
    offset = 0
    for size in fold_sizes:
        folds.append(remaining.iloc[offset : offset + size])
        offset += size
    return warmup_count, folds


def _evaluate_shift(
    data: pd.DataFrame,
    valid_rows: pd.DataFrame,
    folds: list[pd.DataFrame],
    *,
    shift: int,
    model_version: str,
    config_hash: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    all_baseline_errors: list[float] = []
    all_fused_errors: list[float] = []
    fold_results: list[dict[str, Any]] = []
    bias_stabilities: list[float] = []
    total_alert_changes = 0
    total_saturation_count = 0

    target_by_time = valid_rows.set_index("timestamp_utc")["purpleair_pm25"]
    for fold_index, fold_targets in enumerate(folds, start=1):
        test_times = set(fold_targets["timestamp_utc"])
        test_start = fold_targets["timestamp_utc"].iloc[0]
        test_end = fold_targets["timestamp_utc"].iloc[-1]
        through_fold = data.loc[data["timestamp_utc"] <= test_end]
        trace, _ = run_hardware_rows(
            through_fold,
            alpha_shift=shift,
            model_version=model_version,
            config_hash=config_hash,
        )
        validation = trace.loc[trace["timestamp_utc"].isin(test_times)].copy()
        validation["target"] = validation["timestamp_utc"].map(target_by_time)
        baseline_errors = (
            validation["cams_pm25"] - validation["target"]
        ).astype(float).tolist()
        fused_errors = (
            validation["fused_pm25"] - validation["target"]
        ).astype(float).tolist()
        baseline_mae, baseline_rmse = _metric(baseline_errors)
        fused_mae, fused_rmse = _metric(fused_errors)

        period = trace.loc[
            (trace["timestamp_utc"] >= test_start)
            & (trace["timestamp_utc"] <= test_end)
        ]
        bias_values = period["bias_after_x16"].astype(float).tolist()
        bias_stability = (
            statistics.pstdev(bias_values) if len(bias_values) >= 2 else 0.0
        )
        alert_changes = int(
            period["alert_state_after"].astype(int).diff().abs().fillna(0).sum()
        )
        saturation_count = int(
            period["bias_after_x16"].isin([BIAS_MIN_X16, BIAS_MAX_X16]).sum()
            + period["fused_pm25_x16"].isin([PM25_MIN_X16, PM25_MAX_X16]).sum()
        )
        continuity_hours = int((period["qc_ok"] == 0).sum())
        fold_results.append(
            {
                "fold": fold_index,
                "test_start_utc": test_start,
                "test_end_utc": test_end,
                "valid_target_hours": len(validation),
                "warmup_hours_from_timeline_start": int(
                    (through_fold["timestamp_utc"] < test_start).sum()
                ),
                "baseline_mae": baseline_mae,
                "baseline_rmse": baseline_rmse,
                "fused_mae": fused_mae,
                "fused_rmse": fused_rmse,
                "mae_improvement": (
                    baseline_mae - fused_mae
                    if baseline_mae is not None and fused_mae is not None
                    else None
                ),
                "rmse_improvement": (
                    baseline_rmse - fused_rmse
                    if baseline_rmse is not None and fused_rmse is not None
                    else None
                ),
                "bias_std_x16": bias_stability,
                "alert_state_changes": alert_changes,
                "saturation_count": saturation_count,
                "qc_fail_continuity_hours": continuity_hours,
            }
        )
        all_baseline_errors.extend(baseline_errors)
        all_fused_errors.extend(fused_errors)
        bias_stabilities.append(bias_stability)
        total_alert_changes += alert_changes
        total_saturation_count += saturation_count

    baseline_mae, baseline_rmse = _metric(all_baseline_errors)
    fused_mae, fused_rmse = _metric(all_fused_errors)
    aggregate = {
        "alpha_shift": shift,
        "alpha": f"1/{2 ** shift}",
        "valid_target_hours": len(all_fused_errors),
        "fold_count": len(folds),
        "baseline_mae": baseline_mae,
        "baseline_rmse": baseline_rmse,
        "fused_mae": fused_mae,
        "fused_rmse": fused_rmse,
        "mae_improvement": (
            baseline_mae - fused_mae
            if baseline_mae is not None and fused_mae is not None
            else None
        ),
        "rmse_improvement": (
            baseline_rmse - fused_rmse
            if baseline_rmse is not None and fused_rmse is not None
            else None
        ),
        "bias_std_x16_mean": (
            statistics.fmean(bias_stabilities) if bias_stabilities else None
        ),
        "alert_state_changes": total_alert_changes,
        "saturation_count": total_saturation_count,
        "reference_composite_score": (
            fused_mae
            + 0.20 * statistics.fmean(bias_stabilities)
            + 0.05 * total_alert_changes
            if fused_mae is not None and bias_stabilities
            else None
        ),
    }
    return aggregate, fold_results


def evaluate_alpha_candidates(
    frame: pd.DataFrame,
    *,
    config: dict[str, Any],
    output_dir: str | Path,
    requested_folds: int = 4,
    minimum_valid_hours: int = 16,
) -> dict[str, Any]:
    data = normalize_hourly_input(frame)
    valid = data.loc[
        (data["sample_valid"] == 1)
        & (data["qc_ok"] == 1)
        & data["purpleair_pm25"].notna()
    ].copy()
    hardware = config["hardware_aligned"]
    model_version = str(hardware["model_version"])
    config_hash = processing_config_hash(config, ACTIVE_CONFIG)
    output_dir = Path(output_dir)
    dataset_start = data["timestamp_utc"].min() if not data.empty else None
    dataset_end = data["timestamp_utc"].max() if not data.empty else None
    active_before = int(ACTIVE_CONFIG["selected_alpha_shift"])

    report: dict[str, Any] = {
        "status": "evaluated",
        "dataset_rows": len(data),
        "valid_target_hours": len(valid),
        "dataset_start_utc": dataset_start,
        "dataset_end_utc": dataset_end,
        "dataset_hash": input_fingerprint(data),
        "config_hash": config_hash,
        "model_version": model_version,
        "candidate_shifts": list(ALPHA_SHIFTS),
        "active_alpha_shift_before": active_before,
        "active_alpha_shift_after": active_before,
        "auto_promoted": False,
        "validation": {
            "method": "chronological expanding warm-up with non-overlapping validation blocks",
            "state_reset": "reset to zero at the start of each fold replay",
            "target_policy": "metrics use PurpleAir only when qc_ok=1",
        },
        "aggregates": [],
        "folds": {},
        "best_observed_shift": None,
    }
    if len(valid) < minimum_valid_hours:
        report["status"] = "insufficient_data"
        report["reason"] = (
            f"Need at least {minimum_valid_hours} qc_ok target hours; found {len(valid)}."
        )
    else:
        warmup_count, folds = _folds(valid, requested_folds)
        if not folds:
            report["status"] = "insufficient_data"
            report["reason"] = "Not enough post-warmup target hours for a validation fold."
        else:
            report["validation"]["warmup_valid_target_hours"] = warmup_count
            for shift in ALPHA_SHIFTS:
                aggregate, fold_results = _evaluate_shift(
                    data,
                    valid,
                    folds,
                    shift=shift,
                    model_version=model_version,
                    config_hash=config_hash,
                )
                report["aggregates"].append(aggregate)
                report["folds"][str(shift)] = fold_results
            ranked = sorted(
                report["aggregates"],
                key=lambda item: (
                    float("inf") if item["fused_mae"] is None else item["fused_mae"],
                    item["alpha_shift"],
                ),
            )
            report["best_observed_shift"] = ranked[0]["alpha_shift"]

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(output_dir / "latest_alpha_candidate.json", report)
    aggregates = pd.DataFrame(report["aggregates"])
    if aggregates.empty:
        aggregates = pd.DataFrame(
            columns=[
                "alpha_shift",
                "alpha",
                "valid_target_hours",
                "fold_count",
                "baseline_mae",
                "baseline_rmse",
                "fused_mae",
                "fused_rmse",
                "mae_improvement",
                "rmse_improvement",
                "bias_std_x16_mean",
                "alert_state_changes",
                "saturation_count",
                "reference_composite_score",
            ]
        )
    write_csv_atomic(aggregates, output_dir / "latest_alpha_candidate.csv")

    lines = [
        "# Alpha Candidate Evaluation",
        "",
        f"- Status: `{report['status']}`",
        f"- Dataset: {dataset_start} to {dataset_end}",
        f"- Dataset rows: {len(data)}",
        f"- Valid `qc_ok=1` target hours: {len(valid)}",
        f"- Active alpha shift remains: {active_before}",
        "- Automatic promotion: **disabled**",
        "- Validation: chronological expanding warm-up; state resets to zero for each fold replay.",
        "- PurpleAir error metrics use only `qc_ok=1` hours.",
        "",
    ]
    if report["status"] == "evaluated":
        lines.extend(
            [
                f"- Best observed shift by aggregate fused MAE: {report['best_observed_shift']} "
                "(candidate only; manual review required)",
                "",
                "| Shift | Alpha | Valid hours | Folds | CAMS MAE | Fused MAE | MAE improvement | "
                "CAMS RMSE | Fused RMSE | Bias std x16 | Alert changes | Saturations |",
                "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in report["aggregates"]:
            lines.append(
                f"| {item['alpha_shift']} | {item['alpha']} | {item['valid_target_hours']} | "
                f"{item['fold_count']} | {item['baseline_mae']:.6f} | {item['fused_mae']:.6f} | "
                f"{item['mae_improvement']:.6f} | {item['baseline_rmse']:.6f} | "
                f"{item['fused_rmse']:.6f} | {item['bias_std_x16_mean']:.6f} | "
                f"{item['alert_state_changes']} | {item['saturation_count']} |"
            )
    else:
        lines.extend([f"- Reason: {report.get('reason')}", ""])
    _write_text_atomic(
        output_dir / "latest_alpha_candidate.md",
        "\n".join(lines) + "\n",
    )
    return report


__all__ = ["ALPHA_SHIFTS", "evaluate_alpha_candidates"]
