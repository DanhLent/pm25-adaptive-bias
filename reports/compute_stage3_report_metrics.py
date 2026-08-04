from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "pm25_fused_hourly_dataset.csv"
OUTPUT_MD = PROJECT_ROOT / "reports" / "STAGE3_REPORT_METRICS.md"
OUTPUT_JSON = PROJECT_ROOT / "reports" / "stage3_report_metrics.json"


def as_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def metric(rows: list[dict[str, str]], estimate_col: str, reference_col: str) -> dict[str, float | int]:
    errors: list[float] = []
    for row in rows:
        estimate = as_float(row.get(estimate_col))
        reference = as_float(row.get(reference_col))
        if estimate is None or reference is None:
            continue
        errors.append(estimate - reference)

    n = len(errors)
    if n == 0:
        return {"n": 0, "mae": math.nan, "rmse": math.nan}

    mae = sum(abs(err) for err in errors) / n
    rmse = math.sqrt(sum(err * err for err in errors) / n)
    return {"n": n, "mae": mae, "rmse": rmse}


def count_present(rows: list[dict[str, str]], column: str) -> int:
    return sum(1 for row in rows if as_float(row.get(column)) is not None)


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    times = [row["time"] for row in rows if row.get("time")]
    columns = rows[0].keys() if rows else []

    required = [
        "cams_pm25",
        "pa_pm25_hourly",
        "fused_pm25",
        "pa_pm25_hourly_loose",
        "pa_pm25_hourly_strict",
    ]
    missing_columns = [column for column in required if column not in columns]
    if missing_columns:
        raise KeyError(f"Missing required columns: {', '.join(missing_columns)}")

    cams_vs_pa = metric(rows, "cams_pm25", "pa_pm25_hourly")
    fused_vs_pa = metric(rows, "fused_pm25", "pa_pm25_hourly")

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_csv": str(INPUT_CSV.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "formula": {
            "mae": "mean(abs(estimate - pa_pm25_hourly))",
            "rmse": "sqrt(mean((estimate - pa_pm25_hourly)^2))",
            "reference": "pa_pm25_hourly",
            "estimate_columns": ["cams_pm25", "fused_pm25"],
            "unit": "micrograms per cubic meter",
        },
        "counts": {
            "rows_total": len(rows),
            "time_start": min(times) if times else None,
            "time_end": max(times) if times else None,
            "cams_pm25": count_present(rows, "cams_pm25"),
            "pa_pm25_hourly_loose": count_present(rows, "pa_pm25_hourly_loose"),
            "pa_pm25_hourly": count_present(rows, "pa_pm25_hourly"),
            "pa_pm25_hourly_strict": count_present(rows, "pa_pm25_hourly_strict"),
            "fused_pm25": count_present(rows, "fused_pm25"),
            "rows_with_cams_and_pa": cams_vs_pa["n"],
            "rows_with_fused_and_pa": fused_vs_pa["n"],
        },
        "metrics": {
            "cams_pm25_vs_pa_pm25_hourly": cams_vs_pa,
            "fused_pm25_vs_pa_pm25_hourly": fused_vs_pa,
        },
    }

    OUTPUT_JSON.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    md = f"""# Stage 3 Report Metrics

Generated from `{result["input_csv"]}`.

## Definition

- Reference column: `pa_pm25_hourly`.
- CAMS baseline error: `cams_pm25 - pa_pm25_hourly`.
- Fusion/self-calibration error: `fused_pm25 - pa_pm25_hourly`.
- MAE: `mean(abs(error))`.
- RMSE: `sqrt(mean(error^2))`.
- Unit for MAE/RMSE in the report: `\\pmunit{{}}`.

These metrics are computed from the processed hourly/loose overlap dataset. They are not the 1h/3h/6h forecast diagnostics in `reports/STAGE_2_EVALUATION.md`.

## Counts

| Item | Value |
| --- | ---: |
| Total rows | {result["counts"]["rows_total"]} |
| Time range | {result["counts"]["time_start"]} to {result["counts"]["time_end"]} |
| `cams_pm25` present | {result["counts"]["cams_pm25"]} |
| `pa_pm25_hourly_loose` present | {result["counts"]["pa_pm25_hourly_loose"]} |
| `pa_pm25_hourly` present | {result["counts"]["pa_pm25_hourly"]} |
| `pa_pm25_hourly_strict` present | {result["counts"]["pa_pm25_hourly_strict"]} |
| `fused_pm25` present | {result["counts"]["fused_pm25"]} |
| Rows with CAMS and PA | {result["counts"]["rows_with_cams_and_pa"]} |
| Rows with fused and PA | {result["counts"]["rows_with_fused_and_pa"]} |

## Metrics

| Comparison | n | MAE | RMSE |
| --- | ---: | ---: | ---: |
| `cams_pm25` vs `pa_pm25_hourly` | {cams_vs_pa["n"]} | {cams_vs_pa["mae"]:.4f} | {cams_vs_pa["rmse"]:.4f} |
| `fused_pm25` vs `pa_pm25_hourly` | {fused_vs_pa["n"]} | {fused_vs_pa["mae"]:.4f} | {fused_vs_pa["rmse"]:.4f} |

## Notes

- `pa_pm25_hourly_strict = 0` because the PurpleAir history data used here is hourly aggregate data; it does not provide multiple sub-hourly samples inside each hour for the stricter multi-sample condition.
- The 127 rows are hourly/loose overlap rows between PurpleAir VNU-HCM 9520 and CAMS/Open-Meteo, not a long-term full validation set.
"""
    OUTPUT_MD.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
