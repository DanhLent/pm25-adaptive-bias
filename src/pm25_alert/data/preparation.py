from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from pm25_alert.data.canonical import (
    append_canonical_atomic,
    build_hourly_from_canonical,
    find_canonical_gaps,
    load_legacy_hourly,
    normalize_manual_purpleair_csv,
    write_csv_atomic,
)
from pm25_alert.data.loading import load_cams


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _time_range(frame: pd.DataFrame, column: str = "time") -> tuple[str | None, str | None]:
    if frame.empty or column not in frame:
        return None, None
    values = pd.to_datetime(frame[column], errors="coerce", utc=True)
    return (
        values.min().isoformat() if values.notna().any() else None,
        values.max().isoformat() if values.notna().any() else None,
    )


def _old_or_disagreement(samples: pd.DataFrame, config: dict) -> int:
    if not {"pa_pm25_a", "pa_pm25_b"}.issubset(samples.columns):
        return 0
    policy = config["purpleair_qc_policy"]
    absolute = (samples["pa_pm25_a"] - samples["pa_pm25_b"]).abs()
    mean = samples[["pa_pm25_a", "pa_pm25_b"]].mean(axis=1)
    relative = absolute / mean.where(mean > 0)
    return int(
        (
            (absolute >= float(policy["severe_abs_diff_min"]))
            | (relative >= float(policy["severe_rel_diff_min"]))
        ).sum()
    )


def build_cams_hourly(root: Path, config: dict) -> pd.DataFrame:
    interim = root / config["paths"]["interim_data_dir"]
    canonical = interim / "cams_all_available.csv"
    raw_dir = root / config["paths"]["raw_data_dir"]
    live_dir = root / config["data_sources"]["incremental"]["raw_append_dir"]
    raw_candidates = sorted(
        path
        for path in raw_dir.glob("*.csv")
        if "open" in path.name.lower() or "cams" in path.name.lower()
    )
    live_candidates = sorted(live_dir.glob("openmeteo_cams_pm25_increment_*.csv"))
    candidates = [*raw_candidates]
    if canonical.exists():
        candidates.append(canonical)
    candidates.extend(live_candidates)
    if not candidates:
        raise FileNotFoundError("No canonical, raw, or live CAMS CSV is available.")

    frames = []
    for path in candidates:
        frame = load_cams(path, config["project"]["timezone"])
        frame["source_file"] = path.name
        frames.append(frame)
    cams = (
        pd.concat(frames, ignore_index=True, sort=False)
        .sort_values("time")
        .drop_duplicates("time", keep="last")
        .reset_index(drop=True)
    )
    cams["time"] = pd.to_datetime(cams["time"], errors="coerce", utc=True)
    cams["cams_pm25"] = pd.to_numeric(cams["cams_pm25"], errors="coerce")
    cams = cams.dropna(subset=["time", "cams_pm25"])
    write_csv_atomic(cams, canonical)
    return (
        cams.set_index("time")[["cams_pm25"]]
        .resample(config["preprocessing"]["cams_resample_rule"])
        .mean()
        .dropna(subset=["cams_pm25"])
        .reset_index()
    )


def build_cams_led_timeline(
    cams_hourly: pd.DataFrame,
    purpleair_hourly: pd.DataFrame,
    timezone_name: str,
) -> pd.DataFrame:
    cams = cams_hourly.copy()
    pa = purpleair_hourly.copy()
    cams["time"] = pd.to_datetime(cams["time"], errors="coerce", utc=True)
    if not pa.empty:
        pa["time"] = pd.to_datetime(pa["time"], errors="coerce", utc=True)
    timeline = cams.merge(pa, on="time", how="left", validate="one_to_one")
    timeline = timeline.sort_values("time").reset_index(drop=True)
    timeline["sample_valid"] = 1
    timeline["qc_ok"] = pd.to_numeric(
        timeline.get("qc_ok", 0),
        errors="coerce",
    ).fillna(0).astype(int)
    timeline["qc_score"] = pd.to_numeric(
        timeline.get("qc_score", 0.0),
        errors="coerce",
    ).fillna(0.0).clip(0.0, 1.0)
    timeline["source_type"] = timeline.get(
        "source_type",
        pd.Series(index=timeline.index, dtype="object"),
    ).fillna("purpleair_missing")
    timeline["pa_pm25_hourly_source"] = timeline.get(
        "pa_pm25_hourly_source",
        pd.Series(index=timeline.index, dtype="object"),
    ).fillna("missing")
    timeline["qc_reason_codes"] = timeline.get(
        "qc_reason_codes",
        pd.Series(index=timeline.index, dtype="object"),
    ).fillna("purpleair_missing")
    local = timeline["time"].dt.tz_convert(timezone_name)
    timeline["timestamp_utc"] = timeline["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    timeline["time_local"] = local.astype(str)
    timeline["hour"] = local.dt.hour.astype(int)
    return timeline


def prepare_canonical_data(root: Path, config: dict) -> dict[str, Any]:
    pa_cfg = config["data_sources"]["purpleair"]
    timezone_name = config["project"]["timezone"]
    canonical_path = root / pa_cfg["canonical_live_csv"]
    sensor_index = int(pa_cfg["sensor_index"])
    resolution = int(pa_cfg["default_average_minutes"])
    data_product = str(pa_cfg.get("data_product", "pm25_cf_1"))
    schema_version = int(pa_cfg.get("canonical_schema_version", 1))

    manual_frames = []
    manual_sources: list[dict[str, Any]] = []
    for configured in pa_cfg.get("manual_csv_inputs", []):
        relative = Path(configured)
        path = relative if relative.is_absolute() else root / relative
        if not path.exists():
            manual_sources.append({"path": str(configured), "status": "missing"})
            continue
        frame = normalize_manual_purpleair_csv(
            path,
            sensor_index=sensor_index,
            timezone_name=timezone_name,
            resolution_minutes=resolution,
            data_product=data_product,
            schema_version=schema_version,
        )
        frame["raw_source"] = relative.as_posix()
        manual_frames.append(frame)
        start, end = _time_range(frame)
        manual_sources.append(
            {
                "path": relative.as_posix(),
                "status": "imported",
                "sha256": _sha256(path),
                "rows": len(frame),
                "start_utc": start,
                "end_utc": end,
            }
        )

    manual = (
        pd.concat(manual_frames, ignore_index=True, sort=False)
        if manual_frames
        else pd.DataFrame()
    )
    canonical, duplicate_count = append_canonical_atomic(canonical_path, manual)
    gaps = find_canonical_gaps(canonical)

    legacy_path = root / pa_cfg["legacy_hourly_csv"]
    legacy = load_legacy_hourly(legacy_path)
    qc_samples, purpleair_hourly = build_hourly_from_canonical(
        canonical,
        legacy,
        config,
    )
    cams_hourly = build_cams_hourly(root, config)
    timeline = build_cams_led_timeline(cams_hourly, purpleair_hourly, timezone_name)

    interim_dir = root / config["paths"]["interim_data_dir"]
    processed_dir = root / config["paths"]["processed_data_dir"]
    write_csv_atomic(qc_samples, interim_dir / "purpleair_10min_qc.csv")
    write_csv_atomic(purpleair_hourly, interim_dir / "purpleair_hourly.csv")
    write_csv_atomic(timeline, processed_dir / "pm25_hourly_canonical.csv")

    source_counts = purpleair_hourly["source_type"].value_counts(dropna=False).to_dict()
    strict_hours = int((purpleair_hourly["qc_ok"] == 1).sum())
    non_strict_10min = int(
        (purpleair_hourly["source_type"] == "purpleair_10min").sum()
    ) - strict_hours
    legacy_hours = int(
        (purpleair_hourly["source_type"] == "purpleair_legacy_hourly").sum()
    )
    cams_missing_pa = int((timeline["source_type"] == "purpleair_missing").sum())
    severe_count = int(qc_samples["channel_disagree"].fillna(False).sum())
    old_or_count = _old_or_disagreement(qc_samples, config)

    summary: dict[str, Any] = {
        "canonical_root": str(root),
        "canonical_10min_csv": str(canonical_path.relative_to(root)),
        "manual_sources": manual_sources,
        "canonical_rows": len(canonical),
        "canonical_duplicates_removed_this_run": duplicate_count,
        "canonical_start_utc": _time_range(canonical, "timestamp")[0],
        "canonical_end_utc": _time_range(canonical, "timestamp")[1],
        "canonical_gap_count": len(gaps),
        "canonical_gaps": gaps,
        "legacy_hourly_rows_preserved": len(legacy),
        "purpleair_hourly_rows": len(purpleair_hourly),
        "strict_10min_hours": strict_hours,
        "non_strict_10min_hours": non_strict_10min,
        "legacy_fallback_hours": legacy_hours,
        "hourly_source_counts": source_counts,
        "cams_hourly_rows": len(cams_hourly),
        "cams_timeline_start_utc": _time_range(cams_hourly)[0],
        "cams_timeline_end_utc": _time_range(cams_hourly)[1],
        "cams_hours_missing_purpleair": cams_missing_pa,
        "sample_rows": len(qc_samples),
        "old_or_disagreement_rows": old_or_count,
        "new_and_severe_disagreement_rows": severe_count,
        "low_concentration_or_only_rows_recovered": old_or_count - severe_count,
        "raw_sources_modified": False,
    }

    report_lines = [
        "# PM2.5 Data Migration and QC Report",
        "",
        "This report is generated from read-only raw/reference inputs. No CAMS, "
        "PurpleAir legacy, July raw data, or `_codex_inputs/` file was overwritten.",
        "",
        "## Migration",
        "",
        f"- Canonical 10-minute rows: {summary['canonical_rows']}",
        f"- Canonical range UTC: {summary['canonical_start_utc']} to {summary['canonical_end_utc']}",
        f"- Duplicates removed this run: {duplicate_count}",
        f"- Detected canonical gaps: {len(gaps)}",
        f"- Preserved legacy hourly rows: {len(legacy)}",
        f"- Strict 10-minute hours: {strict_hours}",
        f"- Non-strict 10-minute hours: {non_strict_10min}",
        f"- Legacy-only fallback hours: {legacy_hours}",
        f"- CAMS hours retained by LEFT JOIN: {len(timeline)}",
        f"- CAMS hours without PurpleAir: {cams_missing_pa}",
        "",
        "## QC before/after",
        "",
        f"- Sample rows evaluated: {len(qc_samples)}",
        f"- Old absolute-OR-relative disagreement rows: {old_or_count}",
        f"- Required absolute-AND-relative severe rows: {severe_count}",
        f"- Rows recovered from relative-only rejection: {old_or_count - severe_count}",
        f"- Minimum good samples/hour: {config['purpleair_qc_policy']['min_good_samples_per_hour']}",
        f"- Minimum coverage minutes/hour: {config['purpleair_qc_policy']['min_coverage_minutes_per_hour']}",
        f"- Hourly statistic: {config['purpleair_qc_policy']['hourly_statistic']}",
        "",
        "## Manual sources",
        "",
        "```json",
        json.dumps(manual_sources, indent=2),
        "```",
        "",
        "## Source counts",
        "",
        "```json",
        json.dumps(source_counts, indent=2),
        "```",
    ]
    reports_dir = root / config["paths"]["reports_dir"]
    _write_text_atomic(
        reports_dir / "PM25_DATA_MIGRATION_QC_REPORT.md",
        "\n".join(report_lines) + "\n",
    )
    _write_text_atomic(
        reports_dir / "pm25_data_migration_qc.json",
        json.dumps(summary, indent=2, default=str) + "\n",
    )
    return summary


__all__ = [
    "build_cams_hourly",
    "build_cams_led_timeline",
    "prepare_canonical_data",
]
