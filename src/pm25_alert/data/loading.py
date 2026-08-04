from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal local runtimes
    yaml = None


TIMEZONE_UTC_HINTS = ("utc", "gmt", "z")
DEFAULT_RETRY_BACKOFF_SECONDS = (30, 60, 120)
MAX_RETRY_BACKOFF_STEPS = 8


def resolve_retry_backoff_seconds(config: dict[str, Any]) -> tuple[int, ...]:
    """Read the one canonical bounded network-retry policy."""
    operations = config.get("operations", {})
    if operations is None:
        operations = {}
    if not isinstance(operations, dict):
        raise ValueError("operations must be a mapping.")
    values = operations.get("retry_backoff_seconds")
    if values in (None, []):
        return DEFAULT_RETRY_BACKOFF_SECONDS
    if not isinstance(values, (list, tuple)):
        raise ValueError(
            "operations.retry_backoff_seconds must be a list of nonnegative integers."
        )
    if len(values) > MAX_RETRY_BACKOFF_STEPS:
        raise ValueError(
            "operations.retry_backoff_seconds has too many entries; "
            f"maximum is {MAX_RETRY_BACKOFF_STEPS}."
        )
    normalized: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(
                "operations.retry_backoff_seconds must contain only "
                "nonnegative integers."
            )
        normalized.append(value)
    return tuple(normalized)


def find_project_root() -> Path:
    """Return the project root by walking upward from cwd or this file."""
    candidates = [Path.cwd(), Path(__file__).resolve().parent]
    for start in candidates:
        for path in [start, *start.parents]:
            if (path / "CODEX_PM25_PIPELINE_PROMPT.md").exists() or (path / "config.yaml").exists():
                return path
    return Path.cwd()


def load_config(path: str | Path = "config.yaml") -> dict:
    root = find_project_root()
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = root / config_path
    with config_path.open("r", encoding="utf-8") as f:
        if yaml is not None:
            config = yaml.safe_load(f)
        else:
            config = _load_simple_yaml(f.read())
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    """Fail fast for policy values that would make data or RTL semantics unsafe."""
    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a mapping.")
    resolve_retry_backoff_seconds(config)

    qc = config.get("purpleair_qc_policy", {})
    if qc:
        min_good = int(qc.get("min_good_samples_per_hour", 4))
        min_coverage = int(qc.get("min_coverage_minutes_per_hour", 30))
        abs_min = float(qc.get("severe_abs_diff_min", 10.0))
        rel_min = float(qc.get("severe_rel_diff_min", 0.35))
        value_min = float(qc.get("valid_pm25_min", 0.0))
        value_max = float(qc.get("valid_pm25_max", 1000.0))
        statistic = str(qc.get("hourly_statistic", "median"))
        if min_good < 1:
            raise ValueError("purpleair_qc_policy.min_good_samples_per_hour must be at least 1.")
        if min_coverage < 0 or min_coverage > 59:
            raise ValueError("purpleair_qc_policy.min_coverage_minutes_per_hour must be in 0..59.")
        if abs_min < 0 or rel_min < 0:
            raise ValueError("PurpleAir disagreement thresholds must be non-negative.")
        if value_min < 0 or value_max <= value_min:
            raise ValueError("PurpleAir valid PM2.5 bounds are invalid.")
        if statistic not in {"median", "mean"}:
            raise ValueError("purpleair_qc_policy.hourly_statistic must be 'median' or 'mean'.")

    data_sources = config.get("data_sources", {})
    pa = data_sources.get("purpleair", {}) if isinstance(data_sources, dict) else {}
    if pa:
        average = int(pa.get("default_average_minutes", 10))
        overlap = float(pa.get("incremental_overlap_hours", 2))
        reconcile = float(pa.get("reconciliation_hours", 72))
        if average <= 0:
            raise ValueError("PurpleAir default_average_minutes must be positive.")
        if overlap < 0:
            raise ValueError("PurpleAir incremental_overlap_hours must be non-negative.")
        if reconcile <= 0:
            raise ValueError("PurpleAir reconciliation_hours must be positive.")

    hardware = config.get("hardware_aligned", {})
    if hardware:
        if int(hardware.get("scale", 16)) != 16:
            raise ValueError("hardware_aligned.scale must remain x16 for core v1.")
        shift = int(hardware.get("active_alpha_shift", 3))
        if shift not in {2, 3, 4, 5, 6}:
            raise ValueError("hardware_aligned.active_alpha_shift must be one of 2..6.")


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if any(ch in value for ch in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_simple_yaml(text: str) -> dict:
    """Parse the flat two-level config.yaml used by this project."""
    config: dict[str, Any] = {}
    current_section: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current_section = line[:-1].strip()
            config[current_section] = {}
            continue
        if current_section is None or ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        config[current_section][key.strip()] = _parse_scalar(value)
    return config


def find_csv_files(raw_dir: str | Path = "data/raw") -> list[Path]:
    root = find_project_root()
    raw_path = Path(raw_dir)
    if not raw_path.is_absolute():
        raw_path = root / raw_path
    return sorted(raw_path.glob("*.csv"))


def _normalize(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(name)).strip("_")


def is_datetime_candidate_column(df: pd.DataFrame, col: str) -> bool:
    """Return True only for plausible datetime columns, not arbitrary numeric values."""
    norm = _normalize(col)
    explicitly_time_named = norm in {"time", "datetime", "date_time", "timestamp", "date"} or any(
        token in norm for token in ("time", "date", "seen", "created")
    )
    if explicitly_time_named:
        return True
    return pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col])


def detect_csv_format(path: str | Path) -> tuple[str, str]:
    """Return a validated `(delimiter, decimal)` pair for supported CSV inputs."""
    path = Path(path)
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:65536]
    if not sample.strip():
        raise ValueError(f"CSV file is empty: {path}")

    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        first_nonempty = next((line for line in sample.splitlines() if line.strip()), "")
        counts = {candidate: first_nonempty.count(candidate) for candidate in ",;\t|"}
        delimiter, count = max(counts.items(), key=lambda item: item[1])
        if count == 0:
            raise ValueError(f"Could not detect a supported CSV delimiter for {path}.")

    decimal = "."
    if delimiter == ";":
        quoted_decimal_comma = re.search(r'"?\s*[+-]?\d+,\d+\s*"?', sample)
        if quoted_decimal_comma:
            decimal = ","
    return delimiter, decimal


def _read_header_candidates(
    path: Path,
    max_rows: int = 20,
    delimiter: str | None = None,
) -> list[tuple[int, list[str]]]:
    rows: list[tuple[int, list[str]]] = []
    delimiter = delimiter or detect_csv_format(path)[0]
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for i, row in zip(range(max_rows), reader):
            if row:
                rows.append((i, [cell.strip() for cell in row]))
    return rows


def detect_csv_header_row(path: str | Path, delimiter: str | None = None) -> int:
    """Find the row that is most likely to contain data column names."""
    path = Path(path)
    delimiter = delimiter or detect_csv_format(path)[0]
    best_row = 0
    best_score = -1
    for row_idx, row in _read_header_candidates(path, delimiter=delimiter):
        normalized = [_normalize(cell) for cell in row]
        score = 0
        if any(name in {"time", "datetime", "date_time", "date"} for name in normalized):
            score += 6
        if any("pm2_5" in name or "pm25" in name or "pm2_5" in name.replace("__", "_") for name in normalized):
            score += 3
        if any(name.endswith("_a") or name == "a" for name in normalized):
            score += 1
        if any(name.endswith("_b") or name == "b" for name in normalized):
            score += 1
        if len(row) >= 2:
            score += 1
        if score > best_score:
            best_score = score
            best_row = row_idx
    return best_row


def read_csv_smart(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    path = Path(path)
    provided_separator = kwargs.pop("sep", kwargs.pop("delimiter", None))
    detected_delimiter, detected_decimal = detect_csv_format(path)
    delimiter = provided_separator or detected_delimiter
    decimal = kwargs.pop("decimal", detected_decimal)
    header_row = kwargs.pop("skiprows", detect_csv_header_row(path, delimiter))
    frame = pd.read_csv(
        path,
        skiprows=header_row,
        encoding=kwargs.pop("encoding", "utf-8-sig"),
        sep=delimiter,
        decimal=decimal,
        **kwargs,
    )
    if len(frame.columns) == 1:
        header = str(frame.columns[0])
        other_delimiters = [candidate for candidate in ",;\t|" if candidate != delimiter]
        if any(candidate in header for candidate in other_delimiters):
            raise ValueError(
                f"CSV dialect validation failed for {path}: parsed one column "
                f"but the header still contains a delimiter."
            )
    return frame


def read_open_meteo_metadata(path: str | Path) -> dict[str, Any]:
    """Read key/value metadata rows before the detected data header, if present."""
    path = Path(path)
    header_row = detect_csv_header_row(path)
    if header_row < 2:
        return {}
    rows = _read_header_candidates(path, max_rows=header_row)
    if len(rows) < 2:
        return {}
    keys = rows[0][1]
    values = rows[1][1]
    metadata: dict[str, Any] = {}
    for key, value in zip(keys, values):
        key = _normalize(key)
        try:
            metadata[key] = float(value)
        except (TypeError, ValueError):
            metadata[key] = value
    return metadata


def infer_file_role(path: str | Path, df: pd.DataFrame) -> str:
    """Return 'cams', 'purpleair', or 'unknown'."""
    path = Path(path)
    text = " ".join([path.name, *map(str, df.columns)]).lower()
    cams_score = sum(clue in text for clue in ("open-meteo", "open_meteo", "cams", "pm2_5", "latitude", "longitude", "elevation"))
    pa_score = sum(clue in text for clue in ("purpleair", "purple", "pm25", "pm2.5", "cf_1", "atm", "channel", "sensor", "last_seen", "created_at"))

    cols = list(df.columns)
    numeric_cols = [col for col in cols if pd.api.types.is_numeric_dtype(pd.to_numeric(df[col], errors="coerce"))]
    normalized = [_normalize(col) for col in cols]
    has_ab_pair = any(name.endswith("_a") or name == "a" for name in normalized) and any(
        name.endswith("_b") or name == "b" for name in normalized
    )
    if has_ab_pair and len(numeric_cols) >= 2:
        pa_score += 4
    if "open-meteo" in path.name.lower() or "pm2_5" in text:
        cams_score += 3
    if pa_score > cams_score:
        return "purpleair"
    if cams_score > pa_score:
        return "cams"
    return "unknown"


def infer_datetime_column(df: pd.DataFrame) -> str:
    candidates = []
    for col in df.columns:
        if not is_datetime_candidate_column(df, col):
            continue
        norm = _normalize(col)
        score = 0
        if norm in {"time", "datetime", "date_time", "timestamp", "date"}:
            score += 10
        if any(token in norm for token in ("time", "date", "seen", "created")):
            score += 4
        parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
        valid_fraction = parsed.notna().mean() if len(parsed) else 0
        if valid_fraction > 0.8:
            score += 5
        elif valid_fraction > 0.4:
            score += 2
        if score:
            candidates.append((score, col))
    if not candidates:
        raise ValueError("Could not infer a datetime column.")
    return sorted(candidates, reverse=True)[0][1]


def infer_cams_pm25_column(df: pd.DataFrame) -> str:
    candidates = []
    for col in df.columns:
        norm = _normalize(col)
        score = 0
        if "pm2_5" in norm or "pm25" in norm or "pm_2_5" in norm:
            score += 10
        if "ug" in norm or "m3" in norm:
            score += 1
        numeric_fraction = pd.to_numeric(df[col], errors="coerce").notna().mean()
        if numeric_fraction > 0.8:
            score += 3
        if "time" in norm or "date" in norm:
            score -= 10
        if score > 0:
            candidates.append((score, col))
    if not candidates:
        numeric_cols = [col for col in df.columns if pd.to_numeric(df[col], errors="coerce").notna().mean() > 0.8]
        if not numeric_cols:
            raise ValueError("Could not infer CAMS PM2.5 column.")
        return numeric_cols[0]
    return sorted(candidates, reverse=True)[0][1]


def infer_purpleair_pm25_columns(df: pd.DataFrame) -> dict:
    """Return mapping of likely PurpleAir PM2.5 columns, including A/B if available."""
    mapping: dict[str, str] = {}
    numeric_cols = [
        col
        for col in df.columns
        if pd.to_numeric(df[col], errors="coerce").notna().mean() > 0.5 and "time" not in _normalize(col) and "date" not in _normalize(col)
    ]
    for col in numeric_cols:
        norm = _normalize(col)
        if norm.endswith("_a") or norm == "a" or "channel_a" in norm or norm.endswith(" a"):
            mapping["a"] = col
        elif norm.endswith("_b") or norm == "b" or "channel_b" in norm or norm.endswith(" b"):
            mapping["b"] = col

    pm_candidates = []
    for col in numeric_cols:
        norm = _normalize(col)
        score = 0
        if "pm25" in norm or "pm2_5" in norm or "pm_2_5" in norm or "pm2_5" in norm.replace("__", "_"):
            score += 8
        if "cf_1" in norm or "atm" in norm:
            score += 2
        if norm.endswith("_a") or norm.endswith("_b"):
            score += 1
        pm_candidates.append((score, col))

    if "a" not in mapping or "b" not in mapping:
        suffix_a = [col for col in numeric_cols if _normalize(col).endswith("_a")]
        suffix_b = [col for col in numeric_cols if _normalize(col).endswith("_b")]
        if suffix_a and suffix_b:
            mapping.setdefault("a", suffix_a[0])
            mapping.setdefault("b", suffix_b[0])
        elif len(numeric_cols) >= 2:
            mapping.setdefault("a", numeric_cols[0])
            mapping.setdefault("b", numeric_cols[1])

    if pm_candidates:
        mapping["best"] = sorted(pm_candidates, reverse=True)[0][1]
    elif numeric_cols:
        mapping["best"] = numeric_cols[0]
    return mapping


def _standardize_one_datetime(series: pd.Series, time_col: str, timezone: str) -> pd.Series:
    raw = series.astype(str)
    has_utc_hint = any(hint in str(time_col).lower() for hint in TIMEZONE_UTC_HINTS) or raw.str.endswith("Z").any()
    parsed = pd.to_datetime(
        series,
        errors="coerce",
        utc=has_utc_hint,
        format="mixed",
    )
    if getattr(parsed.dt, "tz", None) is None:
        if has_utc_hint:
            parsed = pd.to_datetime(
                series,
                errors="coerce",
                utc=True,
                format="mixed",
            ).dt.tz_convert(timezone)
        else:
            parsed = parsed.dt.tz_localize(timezone, nonexistent="shift_forward", ambiguous="NaT")
    else:
        parsed = parsed.dt.tz_convert(timezone)
    return parsed


def standardize_datetime(df: pd.DataFrame, time_col: str, timezone: str = "Asia/Ho_Chi_Minh") -> pd.DataFrame:
    """Return a DataFrame with standardized datetime column named 'time'."""
    out = df.copy()
    out["time"] = _standardize_one_datetime(out[time_col], time_col, timezone)
    if time_col != "time":
        out = out.drop(columns=[time_col])
    out = out.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    return out


def load_cams(path: str | Path, timezone: str = "Asia/Ho_Chi_Minh") -> pd.DataFrame:
    """Return DataFrame with columns: time, cams_pm25, plus preserved metadata if useful."""
    path = Path(path)
    df = read_csv_smart(path)
    time_col = infer_datetime_column(df)
    pm_col = infer_cams_pm25_column(df)
    out = standardize_datetime(df, time_col, timezone)
    out["cams_pm25"] = pd.to_numeric(out[pm_col], errors="coerce")
    if pm_col != "cams_pm25" and pm_col in out.columns:
        out = out.drop(columns=[pm_col])
    metadata = read_open_meteo_metadata(path)
    for key in ("latitude", "longitude", "elevation", "utc_offset_seconds", "timezone"):
        if key in metadata:
            out[f"source_{key}"] = metadata[key]
    keep_first = ["time", "cams_pm25"]
    rest = [col for col in out.columns if col not in keep_first]
    return out[keep_first + rest]


def _coalesce_numeric_by_normalized_name(df: pd.DataFrame, normalized_names: list[str]) -> pd.Series:
    """Return first non-null numeric value across columns matched by normalized names."""
    norm_to_cols: dict[str, list[str]] = {}
    for col in df.columns:
        norm_to_cols.setdefault(_normalize(col), []).append(col)

    series_list = []
    for name in normalized_names:
        for col in norm_to_cols.get(name, []):
            series_list.append(pd.to_numeric(df[col], errors="coerce"))

    if not series_list:
        return pd.Series(pd.NA, index=df.index, dtype="float64")

    return pd.concat(series_list, axis=1).bfill(axis=1).iloc[:, 0]


def load_purpleair(path: str | Path, timezone: str = "Asia/Ho_Chi_Minh") -> pd.DataFrame:
    """Return DataFrame with time, raw PM2.5 columns, and preserved channel columns if available.

    Stage 3 notes:
    - Older local CSV files may use columns like `VNU-HCM A` and `VNU-HCM B`.
    - PurpleAir API files may use columns like `pm2.5_cf_1_a` and `pm2.5_cf_1_b`.
    - When canonical data concatenates both formats, sparse API columns can be missed by
      percentage-based inference. Therefore, known column families are coalesced explicitly.
    """
    df = read_csv_smart(path)
    time_col = infer_datetime_column(df)
    out = standardize_datetime(df, time_col, timezone)

    # Prefer CF=1 channels when available, then ATM channels, then older local CSV names.
    a_known = _coalesce_numeric_by_normalized_name(
        out,
        [
            "pm2_5_cf_1_a",
            "pm25_cf_1_a",
            "pm2_5_atm_a",
            "pm25_atm_a",
            "vnu_hcm_a",
        ],
    )
    b_known = _coalesce_numeric_by_normalized_name(
        out,
        [
            "pm2_5_cf_1_b",
            "pm25_cf_1_b",
            "pm2_5_atm_b",
            "pm25_atm_b",
            "vnu_hcm_b",
        ],
    )
    best_known = _coalesce_numeric_by_normalized_name(
        out,
        [
            "pm2_5_cf_1",
            "pm25_cf_1",
            "pm2_5_atm",
            "pm25_atm",
        ],
    )

    if a_known.notna().any():
        out["pa_pm25_a_raw"] = a_known
    if b_known.notna().any():
        out["pa_pm25_b_raw"] = b_known
    if best_known.notna().any():
        out["pa_pm25_raw"] = best_known

    # Fallback for older or unexpected column names.
    mapping = infer_purpleair_pm25_columns(out)
    if "pa_pm25_a_raw" not in out.columns and "a" in mapping:
        out["pa_pm25_a_raw"] = pd.to_numeric(out[mapping["a"]], errors="coerce")
    if "pa_pm25_b_raw" not in out.columns and "b" in mapping:
        out["pa_pm25_b_raw"] = pd.to_numeric(out[mapping["b"]], errors="coerce")
    if "pa_pm25_raw" not in out.columns and "best" in mapping:
        out["pa_pm25_raw"] = pd.to_numeric(out[mapping["best"]], errors="coerce")

    return out
