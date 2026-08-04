from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.loading import find_project_root, infer_file_role, load_cams, load_config, load_purpleair, read_csv_smart, standardize_datetime


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def deduplicate_by_time(df: pd.DataFrame, extra_keys: list[str] | None = None) -> tuple[pd.DataFrame, int]:
    time_col = "time" if "time" in df.columns else "timestamp" if "timestamp" in df.columns else None
    if df.empty or time_col is None:
        return df.copy(), 0
    keys = [time_col, *(extra_keys or [])]
    keys = [key for key in keys if key in df.columns]
    before = len(df)
    out = df.sort_values(time_col).drop_duplicates(subset=keys, keep="last").reset_index(drop=True)
    return out, before - len(out)


def _role_from_path(path: Path) -> str:
    try:
        df = read_csv_smart(path, nrows=200)
        return infer_file_role(path, df)
    except Exception:
        name = path.name.lower()
        if "openmeteo" in name or "cams" in name:
            return "cams"
        if "purpleair" in name or "pm25" in name:
            return "purpleair"
    return "unknown"


def _load_cams_any(path: Path, timezone: str) -> pd.DataFrame:
    df = read_csv_smart(path)
    if "cams_pm25" in df.columns and "time" in df.columns:
        out = standardize_datetime(df.copy(), "time", timezone)
        return out.dropna(subset=["time"])
    return load_cams(path, timezone)


def _load_purpleair_any(path: Path, timezone: str) -> pd.DataFrame:
    df = read_csv_smart(path)
    if "time" in df.columns:
        out = standardize_datetime(df.copy(), "time", timezone)
        return out.dropna(subset=["time"])
    return load_purpleair(path, timezone)


def _is_probably_purpleair_live_file(path: Path) -> bool:
    name = path.name.lower()
    return "purpleair" in name or "purple_air" in name


def _collect_input_files(root: Path, cfg: dict) -> list[Path]:
    raw_dir = root / cfg["paths"]["raw_data_dir"]
    live_dir = root / cfg["data_sources"]["incremental"]["raw_append_dir"]
    pa_cfg = cfg["data_sources"].get("purpleair", {})
    canonical_pa = root / pa_cfg.get("canonical_live_csv", "data/live/purpleair/purpleair_live_hourly.csv")

    files = list(raw_dir.glob("*.csv"))
    live_files = sorted(live_dir.glob("*.csv"))
    if canonical_pa.exists():
        files.extend(path for path in live_files if not _is_probably_purpleair_live_file(path))
        files.append(canonical_pa)
    else:
        files.extend(live_files)
    return sorted(dict.fromkeys(files))


def build_canonical_datasets(root: Path | None = None) -> dict:
    root = root or find_project_root()
    cfg = load_config(root / "config.yaml")
    timezone = cfg["project"]["timezone"]
    live_dir = root / cfg["data_sources"]["incremental"]["raw_append_dir"]
    interim_dir = root / cfg["paths"]["interim_data_dir"]
    reports_dir = root / cfg["paths"]["reports_dir"]
    for directory in (live_dir, interim_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)

    files = _collect_input_files(root, cfg)
    cams_frames = []
    pa_frames = []
    warnings = []
    file_rows = []
    for path in files:
        role = _role_from_path(path)
        try:
            if role == "cams":
                df = _load_cams_any(path, timezone)
                df["source_file"] = path.name
                cams_frames.append(df)
            elif role == "purpleair":
                df = _load_purpleair_any(path, timezone)
                df["source_file"] = path.name
                pa_frames.append(df)
            else:
                warnings.append(f"Skipped unknown file role: {path.name}")
                df = pd.DataFrame()
            file_rows.append([path.name, role, len(df)])
        except Exception as exc:
            warnings.append(f"Failed to load {path.name}: {exc}")

    cams_all = pd.concat(cams_frames, ignore_index=True, sort=False) if cams_frames else pd.DataFrame(columns=["time", "cams_pm25"])
    pa_all = pd.concat(pa_frames, ignore_index=True, sort=False) if pa_frames else pd.DataFrame(columns=["time"])
    cams_before = len(cams_all)
    pa_before = len(pa_all)
    cams_all, cams_dupes = deduplicate_by_time(cams_all)
    pa_all, pa_dupes = deduplicate_by_time(pa_all, ["sensor_index"] if "sensor_index" in pa_all.columns else None)
    cams_all.to_csv(interim_dir / "cams_all_available.csv", index=False)
    pa_all.to_csv(interim_dir / "purpleair_all_available.csv", index=False)

    def rng(df: pd.DataFrame) -> str:
        if df.empty or "time" not in df.columns:
            return "n/a"
        return f"{df['time'].min()} to {df['time'].max()}"

    warning_lines = [f"- {warning}" for warning in warnings] if warnings else ["- None."]
    report = [
        "# Stage 3 Append/Dedup Report",
        "",
        f"- Files read: {len(files)}",
        f"- CAMS rows before dedup: {cams_before}",
        f"- CAMS rows after dedup: {len(cams_all)}",
        f"- CAMS duplicates removed: {cams_dupes}",
        f"- CAMS time range: {rng(cams_all)}",
        f"- PurpleAir rows before dedup: {pa_before}",
        f"- PurpleAir rows after dedup: {len(pa_all)}",
        f"- PurpleAir duplicates removed: {pa_dupes}",
        f"- PurpleAir time range: {rng(pa_all)}",
        "",
        "## Files",
        "",
        _markdown_table(["file", "role", "rows_loaded"], file_rows),
        "",
        "## Warnings",
        "",
        *warning_lines,
    ]
    (reports_dir / "STAGE_3_APPEND_DEDUP_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return {
        "files_read": len(files),
        "cams_rows_after": len(cams_all),
        "purpleair_rows_after": len(pa_all),
        "cams_duplicates": cams_dupes,
        "purpleair_duplicates": pa_dupes,
    }


def main() -> None:
    summary = build_canonical_datasets()
    print(summary)


if __name__ == "__main__":
    main()
