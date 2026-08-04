from __future__ import annotations

import math

import numpy as np
import pandas as pd


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    time = pd.to_datetime(out["time"])
    out["hour"] = time.dt.hour
    out["day_of_week"] = time.dt.dayofweek
    out["month"] = time.dt.month
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12)
    return out


def add_lag_features(df: pd.DataFrame, columns: list[str], lags: list[int]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            continue
        for lag in lags:
            out[f"{col}_lag_{lag}h"] = out[col].shift(lag)
    return out


def add_rolling_features(df: pd.DataFrame, columns: list[str], windows: list[int]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            continue
        for window in windows:
            rolling = out[col].rolling(window=window, min_periods=1)
            out[f"{col}_roll_mean_{window}h"] = rolling.mean()
            out[f"{col}_roll_std_{window}h"] = rolling.std().fillna(0)
            out[f"{col}_diff_{window}h"] = out[col].diff(window)
    return out


def add_ema(series: pd.Series, alpha: float) -> pd.Series:
    return series.ewm(alpha=alpha, adjust=False, ignore_na=True).mean()


def assign_alert_level(pm25: float, thresholds: dict) -> str:
    if pm25 is None or (isinstance(pm25, float) and math.isnan(pm25)):
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


def add_forecast_targets(df: pd.DataFrame, horizons: list[int], thresholds: dict) -> pd.DataFrame:
    out = df.copy()
    base_col = "fused_pm25" if "fused_pm25" in out.columns else "cams_pm25"
    out["alert_level_now"] = out[base_col].apply(lambda value: assign_alert_level(value, thresholds))
    for h in horizons:
        target_col = f"target_pm25_{h}h"
        out[target_col] = out[base_col].shift(-h)
        out[f"will_exceed_35_{h}h"] = (out[target_col] > thresholds["moderate"]).astype("boolean")
        out.loc[out[target_col].isna(), f"will_exceed_35_{h}h"] = pd.NA
        out[f"alert_level_{h}h"] = out[target_col].apply(lambda value: assign_alert_level(value, thresholds))
    return out
