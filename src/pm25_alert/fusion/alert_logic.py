from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


def load_config(path: str | Path = "config.yaml") -> dict:
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return _load_simple_yaml(text)


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [_parse_scalar(part.strip()) for part in inner.split(",")]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return float(value) if any(ch in value for ch in ".eE") else int(value)
    except ValueError:
        return value


def _load_simple_yaml(text: str) -> dict:
    config: dict[str, Any] = {}
    stack: list[tuple[int, dict]] = [(-1, config)]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, value = line.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip():
            parent[key] = _parse_scalar(value)
        else:
            parent[key] = {}
            stack.append((indent, parent[key]))
    return config


def safe_clip(value, low, high):
    if pd.isna(value):
        return np.nan
    return min(max(value, low), high)


def classify_alert_level(pm25: float, thresholds: dict) -> str:
    if pd.isna(pm25):
        return "missing"
    if pm25 <= thresholds["good"]:
        return "good"
    if pm25 <= thresholds["moderate"]:
        return "moderate"
    if pm25 <= thresholds["unhealthy_sensitive"]:
        return "unhealthy_sensitive"
    if pm25 <= thresholds["unhealthy"]:
        return "unhealthy"
    return "very_unhealthy"


def compute_sensor_confidence_components(row, cfg: dict) -> dict[str, float]:
    conf_cfg = cfg["fusion_alert"]["confidence"]
    if pd.isna(row.get("pa_pm25_hourly", np.nan)):
        return {
            "confidence_base_source_weight": 0.0,
            "confidence_bad_fraction_factor": 1.0,
            "confidence_valid_sample_factor": 1.0,
            "confidence_channel_agreement_factor": 1.0,
            "sensor_confidence": 0.0,
        }
    source = str(row.get("pa_pm25_hourly_source", "missing")).lower()
    if source == "strict":
        base_weight = float(conf_cfg["strict_source_weight"])
    elif source in {"loose", "loose_fallback"}:
        base_weight = float(conf_cfg["loose_source_weight"])
    else:
        base_weight = float(conf_cfg["missing_source_weight"])

    total = row.get("pa_total_samples_per_hour", np.nan)
    valid = row.get("pa_valid_samples_per_hour", np.nan)
    bad_fraction = row.get("pa_bad_fraction_per_hour", np.nan)
    bad_fraction_factor = 1.0
    valid_sample_factor = 1.0
    channel_agreement_factor = 1.0
    if conf_cfg.get("bad_fraction_penalty", True) and not pd.isna(bad_fraction):
        bad_fraction_factor = safe_clip(1.0 - float(bad_fraction), 0.0, 1.0)
    if conf_cfg.get("low_valid_sample_penalty", True) and not pd.isna(valid):
        min_good = max(float(conf_cfg["min_good_valid_samples_per_hour"]), 1.0)
        valid_sample_factor = safe_clip(float(valid) / min_good, 0.0, 1.0)
    if not pd.isna(total) and float(total) > 0 and "channel_disagree_count" in row:
        disagree_ratio = float(row.get("channel_disagree_count", 0.0)) / float(total)
        channel_agreement_factor = safe_clip(1.0 - disagree_ratio, 0.0, 1.0)
    confidence = base_weight * bad_fraction_factor * valid_sample_factor * channel_agreement_factor
    return {
        "confidence_base_source_weight": float(safe_clip(base_weight, 0.0, 1.0)),
        "confidence_bad_fraction_factor": float(safe_clip(bad_fraction_factor, 0.0, 1.0)),
        "confidence_valid_sample_factor": float(safe_clip(valid_sample_factor, 0.0, 1.0)),
        "confidence_channel_agreement_factor": float(safe_clip(channel_agreement_factor, 0.0, 1.0)),
        "sensor_confidence": float(safe_clip(confidence, 0.0, 1.0)),
    }


def compute_sensor_confidence(row, cfg: dict) -> float:
    return compute_sensor_confidence_components(row, cfg)["sensor_confidence"]


def _raw_residual(row, residual_cfg: dict) -> float:
    residual = row.get("pa_pm25_hourly", np.nan) - row.get("cams_pm25", np.nan)
    limit = float(residual_cfg["max_abs_residual"])
    return safe_clip(residual, -limit, limit)


def compute_single_ema_residual(df, cfg: dict) -> pd.Series:
    residual_cfg = cfg["fusion_alert"]["residual"]
    alpha = float(cfg["fusion_alert"]["single_ema"]["alpha"])
    decay = float(residual_cfg["decay_when_invalid"])
    corr_limit = float(residual_cfg["max_abs_correction"])
    state = 0.0
    values = []
    for _, row in df.iterrows():
        confidence = float(row.get("sensor_confidence", 0.0))
        residual = _raw_residual(row, residual_cfg)
        if confidence > 0 and not pd.isna(residual):
            effective_alpha = safe_clip(alpha * confidence, 0.0, 1.0)
            state = effective_alpha * residual + (1.0 - effective_alpha) * state
        else:
            state = decay * state
        state = safe_clip(state, -corr_limit, corr_limit)
        values.append(state)
    return pd.Series(values, index=df.index, name="residual_single_ema")


def compute_dual_ema_residual(df, cfg: dict) -> pd.DataFrame:
    residual_cfg = cfg["fusion_alert"]["residual"]
    dual_cfg = cfg["fusion_alert"]["dual_ema"]
    decay = float(residual_cfg["decay_when_invalid"])
    corr_limit = float(residual_cfg["max_abs_correction"])
    alpha_fast = float(dual_cfg["alpha_fast"])
    alpha_slow = float(dual_cfg["alpha_slow"])
    trend_gain = float(dual_cfg["trend_gain"])
    fast = 0.0
    slow = 0.0
    rows = []
    for _, row in df.iterrows():
        confidence = float(row.get("sensor_confidence", 0.0))
        residual = _raw_residual(row, residual_cfg)
        if confidence > 0 and not pd.isna(residual):
            effective_fast = safe_clip(alpha_fast * confidence, 0.0, 1.0)
            effective_slow = safe_clip(alpha_slow * confidence, 0.0, 1.0)
            fast = effective_fast * residual + (1.0 - effective_fast) * fast
            slow = effective_slow * residual + (1.0 - effective_slow) * slow
        else:
            fast = decay * fast
            slow = decay * slow
        fast = safe_clip(fast, -corr_limit, corr_limit)
        slow = safe_clip(slow, -corr_limit, corr_limit)
        trend = fast - slow
        correction = safe_clip(slow + trend_gain * trend, -corr_limit, corr_limit)
        rows.append((fast, slow, trend, correction))
    return pd.DataFrame(
        rows,
        index=df.index,
        columns=["residual_fast_ema", "residual_slow_ema", "residual_trend_fast_minus_slow", "residual_dual_ema_correction"],
    )


def compute_linear_early_warning(df, cfg: dict) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    ew_cfg = cfg["fusion_alert"]["early_warning"]
    thresholds = cfg["alert_thresholds"]
    exceed = float(cfg["fusion_alert"]["alert_logic"]["threshold_exceed"])
    window = int(ew_cfg["slope_window_hours"])
    max_slope = float(ew_cfg["max_abs_slope"])
    slope = (df["fused_pm25_stage2"] - df["fused_pm25_stage2"].shift(window)) / window
    out["stage2_linear_slope_pm25_per_hour"] = slope.clip(-max_slope, max_slope)
    for h in ew_cfg["horizons_hours"]:
        forecast_col = f"forecast_pm25_{h}h_linear"
        out[forecast_col] = (df["fused_pm25_stage2"] + h * out["stage2_linear_slope_pm25_per_hour"]).clip(lower=0.0)
        out[f"pred_alert_level_{h}h"] = out[forecast_col].apply(lambda value: classify_alert_level(value, thresholds))
        out[f"pred_will_exceed_35_{h}h"] = (out[forecast_col] > exceed).astype("boolean")
        out.loc[out[forecast_col].isna(), f"pred_will_exceed_35_{h}h"] = pd.NA
    return out


def apply_binary_hysteresis(
    values,
    on_threshold: float,
    off_threshold: float,
    require_consecutive_on: int = 1,
    require_consecutive_off: int = 1,
) -> list:
    state = False
    on_count = 0
    off_count = 0
    states = []
    for value in values:
        if pd.isna(value):
            states.append(state)
            continue
        if not state:
            on_count = on_count + 1 if value >= on_threshold else 0
            if on_count >= require_consecutive_on:
                state = True
                off_count = 0
        else:
            off_count = off_count + 1 if value <= off_threshold else 0
            if off_count >= require_consecutive_off:
                state = False
                on_count = 0
        states.append(state)
    return states


def run_fusion_alert(input_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    out = input_df.copy()
    out["time"] = pd.to_datetime(out["time"])
    out = out.sort_values("time").reset_index(drop=True)
    if "fused_pm25" in out.columns:
        out["fused_pm25_stage1"] = out["fused_pm25"]
    confidence_components = pd.DataFrame([compute_sensor_confidence_components(row, cfg) for _, row in out.iterrows()], index=out.index)
    out = pd.concat([out, confidence_components], axis=1)
    residual_cfg = cfg["fusion_alert"]["residual"]
    out["residual_raw"] = out.apply(lambda row: _raw_residual(row, residual_cfg), axis=1)
    out["residual_single_ema"] = compute_single_ema_residual(out, cfg)
    out["fused_pm25_single_ema"] = out["cams_pm25"] + out["residual_single_ema"]
    dual = compute_dual_ema_residual(out, cfg)
    out = pd.concat([out, dual], axis=1)
    out["fused_pm25_dual_ema"] = out["cams_pm25"] + out["residual_dual_ema_correction"]
    out["fused_pm25_stage2"] = out["fused_pm25_dual_ema"]
    early = compute_linear_early_warning(out, cfg)
    out = pd.concat([out, early], axis=1)
    thresholds = cfg["alert_thresholds"]
    alert_cfg = cfg["fusion_alert"]["alert_logic"]
    out["alert_level_stage2_now"] = out["fused_pm25_stage2"].apply(lambda value: classify_alert_level(value, thresholds))
    out["binary_exceed_35_raw"] = out["fused_pm25_stage2"] >= float(alert_cfg["threshold_exceed"])
    out["binary_exceed_35_hysteresis"] = apply_binary_hysteresis(
        out["fused_pm25_stage2"],
        float(alert_cfg["hysteresis_on"]),
        float(alert_cfg["hysteresis_off"]),
        int(alert_cfg["require_consecutive_on"]),
        int(alert_cfg["require_consecutive_off"]),
    )
    return out
