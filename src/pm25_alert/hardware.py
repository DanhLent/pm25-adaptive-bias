from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from pm25_alert.data.canonical import write_csv_atomic
from pm25_alert.state import (
    StateCompatibilityError,
    canonical_json_hash,
    initial_pipeline_state,
    processing_config_hash,
    read_pipeline_state,
    validate_pipeline_state,
    write_json_atomic,
)
from python_model.fixed_point.pm25_core_v1_fixed import (
    ACTIVE_CONFIG,
    PM25CoreV1Fixed,
    float_to_x16,
)


TRACE_COLUMNS = [
    "timestamp_utc",
    "time_local",
    "hour",
    "sample_valid",
    "qc_ok",
    "qc_score",
    "source_type",
    "qc_reason_codes",
    "cams_pm25",
    "purpleair_pm25",
    "cams_pm25_x16",
    "purpleair_pm25_x16",
    "bias_before_x16",
    "bias_before",
    "residual_x16",
    "residual",
    "error_x16",
    "error",
    "delta_x16",
    "delta",
    "bias_after_x16",
    "bias_after",
    "fused_raw_x16",
    "fused_raw",
    "fused_pm25_x16",
    "fused_pm25",
    "alert_level",
    "alert_state_before",
    "alert_state_after",
    "accepted",
    "result_valid",
    "alpha_shift",
    "model_version",
    "config_hash",
]


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def normalize_hourly_input(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"cams_pm25"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Hardware timeline input is missing columns: {sorted(missing)}")
    out = frame.copy()
    if "timestamp_utc" in out:
        timestamp = pd.to_datetime(out["timestamp_utc"], errors="coerce", utc=True)
    elif "time" in out:
        timestamp = pd.to_datetime(out["time"], errors="coerce", utc=True)
    else:
        raise ValueError("Hardware timeline input needs timestamp_utc or time.")
    out["timestamp_utc"] = timestamp.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out = out.dropna(subset=["timestamp_utc"]).sort_values("timestamp_utc")
    if out["timestamp_utc"].duplicated().any():
        duplicates = out.loc[out["timestamp_utc"].duplicated(), "timestamp_utc"].tolist()
        raise ValueError(f"Hardware timeline has duplicate UTC hours: {duplicates[:5]}")
    sample_valid = (
        out["sample_valid"]
        if "sample_valid" in out
        else pd.Series(1, index=out.index, dtype="int64")
    )
    qc_ok = (
        out["qc_ok"]
        if "qc_ok" in out
        else pd.Series(0, index=out.index, dtype="int64")
    )
    out["sample_valid"] = pd.to_numeric(sample_valid, errors="coerce").fillna(0).astype(int)
    out["qc_ok"] = pd.to_numeric(qc_ok, errors="coerce").fillna(0).astype(int)
    out["cams_pm25"] = pd.to_numeric(out["cams_pm25"], errors="coerce")
    if "pa_pm25_hourly" in out:
        out["purpleair_pm25"] = pd.to_numeric(out["pa_pm25_hourly"], errors="coerce")
    elif "purpleair_pm25" in out:
        out["purpleair_pm25"] = pd.to_numeric(out["purpleair_pm25"], errors="coerce")
    else:
        out["purpleair_pm25"] = pd.NA
    out.loc[out["purpleair_pm25"].isna(), "qc_ok"] = 0
    out.loc[out["cams_pm25"].isna(), "sample_valid"] = 0
    return out.reset_index(drop=True)


def input_fingerprint(frame: pd.DataFrame) -> str:
    normalized = normalize_hourly_input(frame)
    rows = []
    for row in normalized.itertuples(index=False):
        rows.append(
            {
                "timestamp_utc": row.timestamp_utc,
                "sample_valid": int(row.sample_valid),
                "qc_ok": int(row.qc_ok),
                "cams_pm25_x16": (
                    float_to_x16(row.cams_pm25)
                    if not pd.isna(row.cams_pm25)
                    else 0
                ),
                "purpleair_pm25_x16": (
                    float_to_x16(row.purpleair_pm25)
                    if not pd.isna(row.purpleair_pm25)
                    else 0
                ),
                "source_type": str(getattr(row, "source_type", "")),
            }
        )
    return canonical_json_hash(rows)


def run_hardware_rows(
    frame: pd.DataFrame,
    *,
    alpha_shift: int,
    model_version: str,
    config_hash: str,
    initial_state: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    data = normalize_hourly_input(frame)
    initial_state = initial_state or {}
    core = PM25CoreV1Fixed(
        alpha_shift=alpha_shift,
        initial_bias_x16=int(initial_state.get("bias_x16", 0)),
        initial_hysteresis_alert=int(initial_state.get("hysteresis_state", 0)),
        sample_index=int(initial_state.get("sample_index", 0)),
    )
    rows: list[dict[str, Any]] = []
    scale = int(ACTIVE_CONFIG["scale"])
    for source in data.to_dict(orient="records"):
        cams = _optional_float(source.get("cams_pm25"))
        purpleair = _optional_float(source.get("purpleair_pm25"))
        sample_valid = int(source.get("sample_valid", 1))
        qc_ok = int(source.get("qc_ok", 0))
        cams_x16 = float_to_x16(cams) if cams is not None else 0
        pa_x16 = float_to_x16(purpleair) if purpleair is not None else 0
        result = core.step(
            {
                "sample_valid": sample_valid,
                "qc_ok": qc_ok,
                "hour": int(source.get("hour", 0)),
                "cams_pm25_x16": cams_x16,
                "purpleair_pm25_x16": pa_x16,
            }
        )
        qc_score = _optional_float(source.get("qc_score")) or 0.0
        rows.append(
            {
                "timestamp_utc": source["timestamp_utc"],
                "time_local": source.get("time_local"),
                "hour": int(source.get("hour", 0)),
                "sample_valid": sample_valid,
                "qc_ok": qc_ok,
                "qc_score": qc_score,
                "source_type": source.get("source_type", "purpleair_missing"),
                "qc_reason_codes": source.get("qc_reason_codes", "purpleair_missing"),
                "cams_pm25": cams,
                "purpleair_pm25": purpleair,
                "cams_pm25_x16": cams_x16,
                "purpleair_pm25_x16": pa_x16,
                "bias_before_x16": result["learned_bias_before_x16"],
                "bias_before": result["learned_bias_before_x16"] / scale,
                "residual_x16": result["residual_x16"],
                "residual": result["residual_x16"] / scale,
                "error_x16": result["error_x16"],
                "error": result["error_x16"] / scale,
                "delta_x16": result["delta_x16"],
                "delta": result["delta_x16"] / scale,
                "bias_after_x16": result["learned_bias_after_x16"],
                "bias_after": result["learned_bias_after_x16"] / scale,
                "fused_raw_x16": result["fused_raw_x16"],
                "fused_raw": result["fused_raw_x16"] / scale,
                "fused_pm25_x16": result["fused_pm25_x16"],
                "fused_pm25": result["fused_pm25_x16"] / scale,
                "alert_level": result["alert_level"],
                "alert_state_before": result["hysteresis_alert_before"],
                "alert_state_after": result["hysteresis_alert_after"],
                "accepted": result["accepted"],
                "result_valid": result["result_valid"],
                "alpha_shift": alpha_shift,
                "model_version": model_version,
                "config_hash": config_hash,
            }
        )
    trace = pd.DataFrame(rows, columns=TRACE_COLUMNS)
    return trace, core.export_state()


def process_hardware_timeline(
    input_frame: pd.DataFrame,
    *,
    config: dict[str, Any],
    trace_path: str | Path,
    state_path: str | Path,
) -> dict[str, Any]:
    hardware = config["hardware_aligned"]
    alpha_shift = int(hardware["active_alpha_shift"])
    model_version = str(hardware["model_version"])
    config_hash = processing_config_hash(config, ACTIVE_CONFIG)
    state_path = Path(state_path)
    trace_path = Path(trace_path)
    data = normalize_hourly_input(input_frame)
    previous_state = read_pipeline_state(state_path)
    mode = "full_replay"
    replay_reason = "no_compatible_state"
    base_trace = pd.DataFrame(columns=TRACE_COLUMNS)
    rows_to_process = data
    initial_state = initial_pipeline_state(
        config_hash=config_hash,
        model_version=model_version,
        active_alpha_shift=alpha_shift,
    )

    if previous_state is not None:
        try:
            validate_pipeline_state(
                previous_state,
                config_hash=config_hash,
                model_version=model_version,
                active_alpha_shift=alpha_shift,
            )
            last_hour = previous_state.get("last_processed_hour")
            if last_hour:
                prefix = data.loc[data["timestamp_utc"] <= str(last_hour)]
                prefix_hash = input_fingerprint(prefix)
                trace_is_available = trace_path.exists()
                if prefix_hash == previous_state.get("processed_input_hash") and trace_is_available:
                    existing = pd.read_csv(trace_path)
                    base_trace = existing.loc[
                        existing["timestamp_utc"].astype(str) <= str(last_hour)
                    ].copy()
                    rows_to_process = data.loc[
                        data["timestamp_utc"] > str(last_hour)
                    ].copy()
                    initial_state = dict(previous_state)
                    mode = "incremental"
                    replay_reason = "unchanged_processed_prefix"
                else:
                    replay_reason = "historical_input_changed_or_trace_missing"
            else:
                replay_reason = "state_has_no_processed_hour"
        except StateCompatibilityError as exc:
            replay_reason = f"state_incompatible: {exc}"

    new_trace, model_state = run_hardware_rows(
        rows_to_process,
        alpha_shift=alpha_shift,
        model_version=model_version,
        config_hash=config_hash,
        initial_state=initial_state,
    )
    if base_trace.empty:
        trace = new_trace.copy()
    elif new_trace.empty:
        trace = base_trace.copy()
    else:
        trace = pd.concat(
            [base_trace, new_trace],
            ignore_index=True,
            sort=False,
        )
    trace = (
        trace.drop_duplicates("timestamp_utc", keep="last")
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )

    if not trace.empty:
        full_prefix = data.loc[
            data["timestamp_utc"] <= trace["timestamp_utc"].iloc[-1]
        ]
        processed_hash = input_fingerprint(full_prefix)
        last_processed = str(trace["timestamp_utc"].iloc[-1])
    else:
        processed_hash = canonical_json_hash([])
        last_processed = None

    next_state = initial_pipeline_state(
        config_hash=config_hash,
        model_version=model_version,
        active_alpha_shift=alpha_shift,
    )
    if previous_state:
        for field in (
            "last_successful_raw_timestamp",
            "last_reconciliation",
            "last_backup",
            "last_alpha_evaluation",
        ):
            next_state[field] = previous_state.get(field)
    next_state.update(model_state)
    next_state.update(
        {
            "last_processed_hour": last_processed,
            "processed_input_hash": processed_hash,
            "updated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        }
    )

    write_csv_atomic(trace, trace_path)
    write_json_atomic(state_path, next_state)
    return {
        "mode": mode,
        "replay_reason": replay_reason,
        "input_rows": len(data),
        "rows_processed": len(rows_to_process),
        "trace_rows": len(trace),
        "last_processed_hour": last_processed,
        "bias_x16": next_state["bias_x16"],
        "hysteresis_state": next_state["hysteresis_state"],
        "config_hash": config_hash,
        "trace_path": str(trace_path),
        "state_path": str(state_path),
    }


def load_active_config_json() -> dict[str, Any]:
    return json.loads(
        Path("training/configs/core_v1_config.json").read_text(encoding="utf-8")
    )


__all__ = [
    "TRACE_COLUMNS",
    "input_fingerprint",
    "normalize_hourly_input",
    "process_hardware_timeline",
    "run_hardware_rows",
]
