from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.loading import (
    detect_csv_header_row,
    find_project_root,
    infer_cams_pm25_column,
    infer_datetime_column,
    infer_file_role,
    infer_purpleair_pm25_columns,
    is_datetime_candidate_column,
    load_config,
    read_open_meteo_metadata,
    read_csv_smart,
)


def _estimate_sampling_interval(df: pd.DataFrame, time_col: str) -> str:
    parsed = pd.to_datetime(df[time_col], errors="coerce").dropna().sort_values()
    if len(parsed) < 3:
        return "not enough timestamps"
    deltas = parsed.diff().dropna()
    median_delta = deltas.median()
    mode_delta = deltas.mode().iloc[0] if not deltas.mode().empty else median_delta
    return f"median={median_delta}, most_common={mode_delta}"


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def _format_head(df: pd.DataFrame) -> str:
    sample = df.head(5).fillna("")
    return _markdown_table([str(col) for col in sample.columns], sample.astype(str).values.tolist())


def main() -> None:
    root = find_project_root()
    config = load_config(root / "config.yaml")
    raw_dir = root / config["paths"]["raw_data_dir"]
    reports_dir = root / config["paths"]["reports_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    root_csvs = sorted(path for path in root.glob("*.csv") if path.is_file())
    for src in root_csvs:
        dst = raw_dir / src.name
        if not dst.exists():
            shutil.copy2(src, dst)

    csvs = sorted(raw_dir.glob("*.csv"))
    lines = [
        "# Data Inspection",
        "",
        "Original CSV files were not modified. Root CSV files were copied into `data/raw/` when missing.",
        "This report inspects only CSV files under `data/raw/` to avoid duplicate root/raw reporting.",
        "",
    ]

    for path in csvs:
        header_row = detect_csv_header_row(path)
        df = read_csv_smart(path)
        role = infer_file_role(path, df)
        lines.extend([f"## {path.name}", "", f"- Path: `{path}`", f"- Detected header row: {header_row + 1}", f"- Shape: {df.shape}", f"- Inferred role: `{role}`"])
        metadata = read_open_meteo_metadata(path)
        if metadata:
            lines.extend(
                [
                    "",
                    "### Detected Source Metadata",
                    "",
                    f"- Latitude: `{metadata.get('latitude', 'not detected')}`",
                    f"- Longitude: `{metadata.get('longitude', 'not detected')}`",
                    f"- Elevation: `{metadata.get('elevation', 'not detected')}`",
                    f"- Timezone: `{metadata.get('timezone', 'not detected')}`",
                    f"- UTC offset seconds: `{metadata.get('utc_offset_seconds', 'not detected')}`",
                ]
            )
        lines.append("")
        lines.append("### Columns")
        lines.append("")
        lines.append(", ".join(f"`{col}`" for col in df.columns))
        lines.append("")
        lines.append("### Dtypes")
        lines.append("")
        lines.append(_markdown_table(["column", "dtype"], [[col, dtype] for col, dtype in df.dtypes.astype(str).items()]))
        lines.append("")
        lines.append("### First 5 Rows")
        lines.append("")
        lines.append(_format_head(df))
        lines.append("")
        lines.append("### Missing Values")
        lines.append("")
        lines.append(_markdown_table(["column", "missing"], [[col, value] for col, value in df.isna().sum().items()]))
        lines.append("")

        likely_datetime = []
        timestamp_ranges = []
        for col in df.columns:
            if not is_datetime_candidate_column(df, col):
                continue
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() > 0.5:
                likely_datetime.append(col)
                timestamp_ranges.append(f"- `{col}`: {parsed.min()} to {parsed.max()}, sampling {_estimate_sampling_interval(df, col)}")
        try:
            selected_time = infer_datetime_column(df)
        except ValueError:
            selected_time = "not detected"
        try:
            cams_pm = infer_cams_pm25_column(df)
        except ValueError:
            cams_pm = "not detected"
        pa_mapping = infer_purpleair_pm25_columns(df)
        role_pm_line = (
            f"- Likely CAMS PM2.5 column: `{cams_pm}`"
            if role == "cams"
            else f"- Likely primary PM2.5/value column for this file: `{pa_mapping.get('best', cams_pm)}`"
        )

        lines.extend(
            [
                "### Inferred Columns",
                "",
                f"- Likely datetime columns: {', '.join(f'`{c}`' for c in likely_datetime) if likely_datetime else 'none'}",
                f"- Selected datetime column: `{selected_time}`",
                role_pm_line,
                f"- Likely PurpleAir PM2.5 mapping: `{pa_mapping}`",
                "",
                "### Timestamp Ranges",
                "",
            ]
        )
        lines.extend(timestamp_ranges or ["- No parseable timestamp range detected."])
        lines.append("")

    (reports_dir / "data_inspection.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {reports_dir / 'data_inspection.md'}")


if __name__ == "__main__":
    main()
