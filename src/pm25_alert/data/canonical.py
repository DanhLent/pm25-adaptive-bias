from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from pm25_alert.data.loading import (
    infer_datetime_column,
    infer_purpleair_pm25_columns,
    read_csv_smart,
    standardize_datetime,
)
from pm25_alert.data.qc import aggregate_purpleair_hourly, qc_purpleair_samples


PURPLEAIR_10MIN_COLUMNS = [
    "schema_version",
    "timestamp",
    "time",
    "time_local",
    "sensor_index",
    "data_product",
    "resolution_minutes",
    "pm25",
    "pm25_cf_1",
    "pm25_cf_1_a",
    "pm25_cf_1_b",
    "pm25_atm",
    "pm25_atm_a",
    "pm25_atm_b",
    "humidity",
    "temperature",
    "pressure",
    "confidence",
    "channel_flags",
    "channel_flags_auto",
    "channel_flags_manual",
    "source_type",
    "raw_source",
    "fetch_time_utc",
]

PURPLEAIR_IDENTITY_COLUMNS = [
    "sensor_index",
    "timestamp",
    "data_product",
    "resolution_minutes",
]


def _normalized(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(name)).strip("_")


def _known_numeric(frame: pd.DataFrame, names: list[str]) -> pd.Series:
    by_name = {_normalized(column): column for column in frame.columns}
    columns = [by_name[name] for name in names if name in by_name]
    if not columns:
        return pd.Series(float("nan"), index=frame.index, dtype="float64")
    return pd.concat(
        [pd.to_numeric(frame[column], errors="coerce") for column in columns],
        axis=1,
    ).bfill(axis=1).iloc[:, 0]


def _source_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def normalize_manual_purpleair_csv(
    path: str | Path,
    *,
    sensor_index: int,
    timezone_name: str,
    resolution_minutes: int = 10,
    data_product: str = "pm25_cf_1",
    schema_version: int = 1,
) -> pd.DataFrame:
    """Normalize a validated manual CSV without using a sparse Average column."""
    path = Path(path)
    raw = read_csv_smart(path)
    time_column = infer_datetime_column(raw)
    normalized = standardize_datetime(raw, time_column, timezone_name)
    mapping = infer_purpleair_pm25_columns(normalized)

    a = _known_numeric(
        normalized,
        ["pm2_5_cf_1_a", "pm25_cf_1_a", "vnu_hcm_a"],
    )
    b = _known_numeric(
        normalized,
        ["pm2_5_cf_1_b", "pm25_cf_1_b", "vnu_hcm_b"],
    )
    if not a.notna().any() and mapping.get("a") in normalized:
        a = pd.to_numeric(normalized[mapping["a"]], errors="coerce")
    if not b.notna().any() and mapping.get("b") in normalized:
        b = pd.to_numeric(normalized[mapping["b"]], errors="coerce")
    if not a.notna().any() and not b.notna().any():
        raise ValueError(
            f"Manual PurpleAir CSV has no validated A/B PM2.5 columns: {path}"
        )

    aggregate = _known_numeric(
        normalized,
        ["pm2_5_cf_1", "pm25_cf_1"],
    )
    time_utc = normalized["time"].dt.tz_convert("UTC")
    out = pd.DataFrame(index=normalized.index)
    out["schema_version"] = int(schema_version)
    out["timestamp"] = time_utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out["time"] = out["timestamp"]
    out["time_local"] = normalized["time"].astype(str)
    out["sensor_index"] = int(sensor_index)
    out["data_product"] = data_product
    out["resolution_minutes"] = int(resolution_minutes)
    out["pm25_cf_1"] = aggregate
    out["pm25_cf_1_a"] = a
    out["pm25_cf_1_b"] = b
    out["pm25"] = aggregate.combine_first(pd.concat([a, b], axis=1).mean(axis=1))
    for column in PURPLEAIR_10MIN_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    out["source_type"] = "manual_csv"
    out["raw_source"] = path.as_posix()
    out["fetch_time_utc"] = _source_mtime_iso(path)
    return out[PURPLEAIR_10MIN_COLUMNS].sort_values("timestamp").reset_index(drop=True)


def canonical_to_qc_input(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["time"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out["pa_pm25_raw"] = pd.to_numeric(out.get("pm25_cf_1"), errors="coerce")
    out["pa_pm25_a_raw"] = pd.to_numeric(out.get("pm25_cf_1_a"), errors="coerce")
    out["pa_pm25_b_raw"] = pd.to_numeric(out.get("pm25_cf_1_b"), errors="coerce")
    return out


def normalize_canonical_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "timestamp" not in out.columns and "time" in out.columns:
        out["timestamp"] = out["time"]
    timestamp = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out["timestamp"] = timestamp.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out["time"] = out["timestamp"]
    out = out.dropna(subset=["timestamp"]).copy()
    for column in PURPLEAIR_10MIN_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    return out[PURPLEAIR_10MIN_COLUMNS]


def deduplicate_canonical(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    out = normalize_canonical_frame(frame)
    before = len(out)
    out = (
        out.sort_values(PURPLEAIR_IDENTITY_COLUMNS + ["fetch_time_utc"])
        .drop_duplicates(subset=PURPLEAIR_IDENTITY_COLUMNS, keep="last")
        .sort_values(["timestamp", "sensor_index", "data_product"])
        .reset_index(drop=True)
    )
    return out, before - len(out)


def write_csv_atomic(frame: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
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
    temp_path = Path(handle.name)
    try:
        with handle:
            frame.to_csv(handle, index=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def append_canonical_atomic(
    path: str | Path,
    batch: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    path = Path(path)
    frames: list[pd.DataFrame] = []
    if path.exists():
        existing = pd.read_csv(path)
        if not existing.empty:
            frames.append(existing)
    if not batch.empty:
        frames.append(batch)
    combined = (
        pd.concat(frames, ignore_index=True, sort=False)
        if frames
        else pd.DataFrame(columns=PURPLEAIR_10MIN_COLUMNS)
    )
    canonical, duplicate_count = deduplicate_canonical(combined)
    write_csv_atomic(canonical, path)
    return canonical, duplicate_count


def find_canonical_gaps(frame: pd.DataFrame) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if frame.empty:
        return gaps
    data = normalize_canonical_frame(frame)
    data["_time"] = pd.to_datetime(data["timestamp"], errors="coerce", utc=True)
    group_columns = ["sensor_index", "data_product", "resolution_minutes"]
    for keys, group in data.groupby(group_columns, dropna=False):
        ordered = group.dropna(subset=["_time"]).sort_values("_time")
        resolution = int(keys[2])
        delta = ordered["_time"].diff()
        for idx in ordered.index[delta > pd.Timedelta(minutes=resolution * 1.5)]:
            previous = ordered.loc[:idx, "_time"].iloc[-2]
            current = ordered.at[idx, "_time"]
            gaps.append(
                {
                    "sensor_index": keys[0],
                    "data_product": keys[1],
                    "resolution_minutes": resolution,
                    "gap_start_utc": previous.isoformat(),
                    "gap_end_utc": current.isoformat(),
                    "gap_minutes": float((current - previous).total_seconds() / 60.0),
                }
            )
    return gaps


def load_legacy_hourly(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    source = pd.read_csv(path)
    time_column = "timestamp" if "timestamp" in source.columns else "time"
    time = pd.to_datetime(source[time_column], errors="coerce", utc=True).dt.floor("h")
    candidates = [
        column
        for column in ("pm25", "pm25_cf_1", "pm25_atm", "pa_pm25_hourly")
        if column in source.columns
    ]
    if not candidates:
        return pd.DataFrame()
    values = pd.concat(
        [pd.to_numeric(source[column], errors="coerce") for column in candidates],
        axis=1,
    ).bfill(axis=1).iloc[:, 0]
    legacy = pd.DataFrame({"time": time, "pa_pm25_hourly": values}).dropna(
        subset=["time", "pa_pm25_hourly"]
    )
    legacy = legacy.sort_values("time").drop_duplicates("time", keep="last")
    legacy["pa_pm25_hourly_strict"] = pd.NA
    legacy["pa_pm25_hourly_loose"] = legacy["pa_pm25_hourly"]
    legacy["pa_pm25_hourly_source"] = "purpleair_legacy_hourly"
    legacy["source_type"] = "purpleair_legacy_hourly"
    legacy["qc_score"] = 0.0
    legacy["qc_ok"] = 0
    legacy["pa_total_samples_per_hour"] = 1
    legacy["pa_valid_samples_per_hour"] = 1
    legacy["pa_good_samples_per_hour"] = 0
    legacy["pa_single_channel_count"] = 0
    legacy["pa_severe_disagree_count"] = 0
    legacy["pa_bad_samples_per_hour"] = 0
    legacy["pa_bad_fraction_per_hour"] = 0.0
    legacy["pa_coverage_minutes"] = 0.0
    legacy["channel_disagree_count"] = 0
    legacy["qc_reason_codes"] = "legacy_provenance_not_strict"
    return legacy.reset_index(drop=True)


def merge_hourly_sources(
    ten_minute_hourly: pd.DataFrame,
    legacy_hourly: pd.DataFrame,
) -> pd.DataFrame:
    """Prefer any 10-minute-derived hour; use legacy only when that hour is absent."""
    if ten_minute_hourly.empty:
        return legacy_hourly.sort_values("time").reset_index(drop=True)
    if legacy_hourly.empty:
        return ten_minute_hourly.sort_values("time").reset_index(drop=True)
    ten = ten_minute_hourly.copy()
    legacy = legacy_hourly.copy()
    ten["time"] = pd.to_datetime(ten["time"], errors="coerce", utc=True)
    legacy["time"] = pd.to_datetime(legacy["time"], errors="coerce", utc=True)
    occupied = set(ten["time"].dropna())
    legacy = legacy.loc[~legacy["time"].isin(occupied)]
    # Build from records instead of concatenating frames with all-NA columns.
    # This keeps the union of both schemas without relying on pandas' deprecated
    # dtype inference for empty/all-NA columns.
    combined = pd.DataFrame.from_records(
        [*ten.to_dict(orient="records"), *legacy.to_dict(orient="records")]
    )
    combined["time"] = pd.to_datetime(combined["time"], errors="coerce", utc=True)
    return (
        combined.sort_values("time")
        .drop_duplicates("time", keep="first")
        .reset_index(drop=True)
    )


def build_hourly_from_canonical(
    ten_minute: pd.DataFrame,
    legacy_hourly: pd.DataFrame,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    qc_samples = qc_purpleair_samples(canonical_to_qc_input(ten_minute), config)
    ten_hourly = aggregate_purpleair_hourly(
        qc_samples,
        config,
        source_type="purpleair_10min",
    )
    return qc_samples, merge_hourly_sources(ten_hourly, legacy_hourly)


__all__ = [
    "PURPLEAIR_10MIN_COLUMNS",
    "PURPLEAIR_IDENTITY_COLUMNS",
    "append_canonical_atomic",
    "build_hourly_from_canonical",
    "canonical_to_qc_input",
    "deduplicate_canonical",
    "find_canonical_gaps",
    "load_legacy_hourly",
    "merge_hourly_sources",
    "normalize_canonical_frame",
    "normalize_manual_purpleair_csv",
    "write_csv_atomic",
]
