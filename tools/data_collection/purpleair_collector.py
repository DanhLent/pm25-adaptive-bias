from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.canonical import (
    PURPLEAIR_10MIN_COLUMNS,
    append_canonical_atomic,
    find_canonical_gaps,
    write_csv_atomic,
)
from pm25_alert.data.loading import (
    find_project_root,
    load_config,
    resolve_retry_backoff_seconds,
)

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None


NORMALIZED_COLUMNS = PURPLEAIR_10MIN_COLUMNS

FIELD_MAP = {
    "pm2.5_cf_1": "pm25_cf_1",
    "pm2_5_cf_1": "pm25_cf_1",
    "pm25_cf_1": "pm25_cf_1",
    "pm2.5_cf_1_a": "pm25_cf_1_a",
    "pm2_5_cf_1_a": "pm25_cf_1_a",
    "pm25_cf_1_a": "pm25_cf_1_a",
    "pm2.5_cf_1_b": "pm25_cf_1_b",
    "pm2_5_cf_1_b": "pm25_cf_1_b",
    "pm25_cf_1_b": "pm25_cf_1_b",
    "pm2.5_atm": "pm25_atm",
    "pm2_5_atm": "pm25_atm",
    "pm25_atm": "pm25_atm",
    "pm2.5_atm_a": "pm25_atm_a",
    "pm2_5_atm_a": "pm25_atm_a",
    "pm25_atm_a": "pm25_atm_a",
    "pm2.5_atm_b": "pm25_atm_b",
    "pm2_5_atm_b": "pm25_atm_b",
    "pm25_atm_b": "pm25_atm_b",
    "humidity": "humidity",
    "temperature": "temperature",
    "pressure": "pressure",
    "confidence": "confidence",
    "channel_flags": "channel_flags",
    "channel_flags_auto": "channel_flags_auto",
    "channel_flags_manual": "channel_flags_manual",
}


class PurpleAirCollectorError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def resolve_project_root(config_path: str | Path) -> Path:
    path = Path(config_path)
    if path.is_absolute() and path.exists():
        return path.parent
    return find_project_root()


def resolve_config_path(root: Path, config_path: str | Path) -> Path:
    path = Path(config_path)
    return path if path.is_absolute() else root / path


def resolve_sensor_index(
    pa_cfg: dict[str, Any],
    cli_sensor_index: int | None,
    require: bool = True,
) -> int | None:
    value = cli_sensor_index if cli_sensor_index is not None else pa_cfg.get("sensor_index")
    if value in (None, "", "null"):
        if require:
            raise PurpleAirCollectorError(
                "PurpleAir sensor_index is missing. Set data_sources.purpleair.sensor_index "
                "in config.yaml or pass --sensor-index <ID>."
            )
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise PurpleAirCollectorError(
            f"PurpleAir sensor_index must be an integer, got {value!r}."
        ) from exc


def resolve_api_key(pa_cfg: dict[str, Any], require: bool = True) -> str | None:
    env_name = str(pa_cfg.get("api_key_env", "PURPLEAIR_API_KEY"))
    api_key = os.environ.get(env_name)
    if not api_key and require:
        raise PurpleAirCollectorError(
            f"PurpleAir API key is missing. Set {env_name} before running live collection."
        )
    return api_key


def history_window(hours: int, now: datetime | None = None) -> tuple[datetime, datetime]:
    if hours <= 0:
        raise PurpleAirCollectorError("History window hours must be greater than 0.")
    end = now or utc_now()
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    end = end.astimezone(timezone.utc)
    return end - timedelta(hours=hours), end


def _latest_canonical_timestamp(path: Path) -> datetime | None:
    if not path.exists():
        return None
    frame = pd.read_csv(path, usecols=lambda column: column in {"timestamp", "time"})
    if frame.empty:
        return None
    column = "timestamp" if "timestamp" in frame.columns else "time"
    latest = pd.to_datetime(frame[column], errors="coerce", utc=True).max()
    return None if pd.isna(latest) else latest.to_pydatetime()


def select_history_window(
    pa_cfg: dict[str, Any],
    canonical_csv: Path,
    *,
    now: datetime | None = None,
    explicit_hours: int | None = None,
    reconcile: bool = False,
) -> tuple[datetime, datetime, str]:
    end = now or utc_now()
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    end = end.astimezone(timezone.utc)
    if explicit_hours is not None:
        start, _ = history_window(explicit_hours, end)
        return start, end, "explicit_backfill"
    if reconcile:
        hours = float(pa_cfg.get("reconciliation_hours", 72))
        return end - timedelta(hours=hours), end, "reconciliation"
    latest = _latest_canonical_timestamp(canonical_csv)
    if latest is not None:
        overlap = float(pa_cfg.get("incremental_overlap_hours", 2))
        return latest - timedelta(hours=overlap), end, "incremental"
    initial = float(pa_cfg.get("initial_lookback_hours", 72))
    return end - timedelta(hours=initial), end, "initial"


def history_request_params(
    pa_cfg: dict[str, Any],
    start: datetime,
    end: datetime,
    hours: int | None = None,
) -> dict[str, Any]:
    del hours
    fields = pa_cfg.get("fields") or [
        "pm2.5_cf_1",
        "pm2.5_cf_1_a",
        "pm2.5_cf_1_b",
    ]
    return {
        "start_timestamp": int(start.timestamp()),
        "end_timestamp": int(end.timestamp()),
        "average": int(pa_cfg.get("default_average_minutes", 10)),
        "fields": ",".join(fields),
    }


def fetch_history_payload(
    api_key: str,
    sensor_index: int,
    pa_cfg: dict[str, Any],
    start: datetime,
    end: datetime,
    retry_backoff_seconds: tuple[int, ...],
) -> dict[str, Any]:
    if requests is None:
        raise PurpleAirCollectorError(
            "The `requests` package is required for PurpleAir collection."
        )
    url = (
        f"{str(pa_cfg.get('api_base_url', 'https://api.purpleair.com/v1')).rstrip('/')}"
        f"/sensors/{sensor_index}/history"
    )
    backoffs = retry_backoff_seconds
    for attempt in range(len(backoffs) + 1):
        try:
            response = requests.get(
                url,
                params=history_request_params(pa_cfg, start, end),
                headers={"X-API-Key": api_key},
                timeout=60,
            )
            if response.ok:
                payload = response.json()
                if not isinstance(payload, dict):
                    raise PurpleAirCollectorError(
                        "PurpleAir history response was not a JSON object."
                    )
                return payload
            transient = response.status_code in {408, 425, 429} or response.status_code >= 500
            if not transient:
                raise PurpleAirCollectorError(
                    f"PurpleAir history request failed with non-transient HTTP {response.status_code}."
                )
            failure = f"transient HTTP {response.status_code}"
        except PurpleAirCollectorError:
            raise
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
        if attempt >= len(backoffs):
            raise PurpleAirCollectorError(
                f"PurpleAir history request failed after bounded retries ({failure})."
            )
        time.sleep(backoffs[attempt])
    raise AssertionError("unreachable")


def _payload_to_frame(payload: dict[str, Any]) -> pd.DataFrame:
    data = payload.get("data") or []
    fields = payload.get("fields") or []
    return pd.DataFrame(data, columns=fields) if data else pd.DataFrame(columns=fields)


def _coalesce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    found = [pd.to_numeric(frame[column], errors="coerce") for column in columns if column in frame]
    if not found:
        return pd.Series(pd.NA, index=frame.index, dtype="float64")
    return pd.concat(found, axis=1).bfill(axis=1).iloc[:, 0]


def normalize_history_payload(
    payload: dict[str, Any],
    sensor_index: int,
    raw_source: str = "purpleair_history",
    fetch_time_utc: str | None = None,
    *,
    resolution_minutes: int = 10,
    data_product: str = "pm25_cf_1",
    schema_version: int = 1,
    timezone_name: str = "Asia/Ho_Chi_Minh",
) -> pd.DataFrame:
    raw = _payload_to_frame(payload)
    renamed = raw.rename(columns={key: value for key, value in FIELD_MAP.items() if key in raw})
    if "time_stamp" in raw:
        timestamp = pd.to_datetime(raw["time_stamp"], unit="s", utc=True, errors="coerce")
    elif "timestamp" in raw:
        timestamp = pd.to_datetime(raw["timestamp"], unit="s", utc=True, errors="coerce")
    elif "time" in raw:
        timestamp = pd.to_datetime(raw["time"], utc=True, errors="coerce")
    else:
        timestamp = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns, UTC]")

    out = pd.DataFrame(index=raw.index)
    out["schema_version"] = int(schema_version)
    out["timestamp"] = timestamp.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out["time"] = out["timestamp"]
    out["time_local"] = timestamp.dt.tz_convert(timezone_name).astype(str)
    out["sensor_index"] = int(sensor_index)
    out["data_product"] = data_product
    out["resolution_minutes"] = int(resolution_minutes)
    for column in FIELD_MAP.values():
        out[column] = (
            pd.to_numeric(renamed[column], errors="coerce")
            if column in renamed and column not in {
                "channel_flags",
                "channel_flags_auto",
                "channel_flags_manual",
            }
            else renamed[column] if column in renamed else pd.NA
        )
    out["pm25"] = _coalesce_numeric(
        out,
        ["pm25_cf_1", "pm25_atm", "pm25_cf_1_a", "pm25_cf_1_b"],
    )
    out["source_type"] = "purpleair_history_api"
    out["raw_source"] = raw_source
    out["fetch_time_utc"] = fetch_time_utc or iso_utc(utc_now())
    for column in NORMALIZED_COLUMNS:
        if column not in out:
            out[column] = pd.NA
    return (
        out[NORMALIZED_COLUMNS]
        .dropna(subset=["timestamp"])
        .sort_values(["timestamp", "sensor_index"])
        .reset_index(drop=True)
    )


def append_canonical(canonical_csv: Path, batch: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    return append_canonical_atomic(canonical_csv, batch)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


def write_run_log(live_dir: Path, summary: dict[str, Any]) -> None:
    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d_%H%M%S")
    write_json(live_dir / "logs" / f"purpleair_run_{stamp}.json", summary)
    write_json(live_dir / "latest_run.json", summary)


def run_collector(
    config_path: str | Path = "config.yaml",
    sensor_index: int | None = None,
    hours: int | None = None,
    dry_run: bool = False,
    *,
    reconcile: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(config_path)
    cfg = load_config(resolve_config_path(root, config_path))
    pa_cfg = cfg["data_sources"]["purpleair"]
    retry_backoff_seconds = resolve_retry_backoff_seconds(cfg)
    live_dir = root / pa_cfg.get("live_dir", "data/live/purpleair")
    canonical_csv = root / pa_cfg.get(
        "canonical_live_csv",
        "data/live/purpleair/purpleair_10min.csv",
    )
    start, end, window_mode = select_history_window(
        pa_cfg,
        canonical_csv,
        now=now,
        explicit_hours=hours,
        reconcile=reconcile,
    )
    selected_sensor = resolve_sensor_index(pa_cfg, sensor_index, require=False)
    api_key = resolve_api_key(pa_cfg, require=False)
    ran_at = iso_utc(now or utc_now())
    summary: dict[str, Any] = {
        "status": "dry_run" if dry_run else "started",
        "sensor_index": selected_sensor,
        "window_mode": window_mode,
        "start_timestamp": iso_utc(start),
        "end_timestamp": iso_utc(end),
        "average_minutes": int(pa_cfg.get("default_average_minutes", 10)),
        "rows_fetched": 0,
        "rows_after_dedup": None,
        "canonical_live_csv": str(canonical_csv),
        "gap_count": None,
        "last_successful_raw_timestamp": None,
        "retry_backoff_seconds": list(retry_backoff_seconds),
        "ran_at_utc": ran_at,
        "error": None,
    }

    if dry_run:
        params = history_request_params(pa_cfg, start, end)
        print(
            "DRY RUN PurpleAir history "
            f"sensor_index={selected_sensor if selected_sensor is not None else '<missing>'} "
            f"mode={window_mode} start={summary['start_timestamp']} "
            f"end={summary['end_timestamp']} params={params} "
            f"api_key_set={bool(api_key)}"
        )
        return summary

    try:
        selected_sensor = resolve_sensor_index(pa_cfg, sensor_index, require=True)
        api_key = resolve_api_key(pa_cfg, require=True)
        payload = fetch_history_payload(
            api_key,
            selected_sensor,
            pa_cfg,
            start,
            end,
            retry_backoff_seconds,
        )
        stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d_%H%M%S")
        raw_path = live_dir / "raw" / f"purpleair_history_raw_{stamp}.json"
        normalized_path = (
            live_dir / "normalized" / f"purpleair_history_normalized_{stamp}.csv"
        )
        write_json(raw_path, payload)
        batch = normalize_history_payload(
            payload,
            selected_sensor,
            raw_source=raw_path.name,
            fetch_time_utc=ran_at,
            resolution_minutes=int(pa_cfg.get("default_average_minutes", 10)),
            data_product=str(pa_cfg.get("data_product", "pm25_cf_1")),
            schema_version=int(pa_cfg.get("canonical_schema_version", 1)),
            timezone_name=cfg["project"]["timezone"],
        )
        write_csv_atomic(batch, normalized_path)
        canonical, duplicate_count = append_canonical(canonical_csv, batch)
        gaps = find_canonical_gaps(canonical)
        latest = pd.to_datetime(batch["timestamp"], errors="coerce", utc=True).max()
        summary.update(
            {
                "status": "ok",
                "sensor_index": selected_sensor,
                "rows_fetched": int(len(batch)),
                "rows_after_dedup": int(len(canonical)),
                "duplicates_removed": int(duplicate_count),
                "gap_count": len(gaps),
                "last_successful_raw_timestamp": (
                    latest.isoformat() if not pd.isna(latest) else None
                ),
                "raw_response": str(raw_path),
                "normalized_batch_csv": str(normalized_path),
            }
        )
        write_json(live_dir / "collector_state.json", summary)
    except Exception as exc:
        summary.update({"status": "error", "error": str(exc)})
        write_run_log(live_dir, summary)
        if isinstance(exc, PurpleAirCollectorError):
            raise
        raise PurpleAirCollectorError(str(exc)) from exc

    write_run_log(live_dir, summary)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Incrementally fetch and append canonical PurpleAir history."
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--sensor-index", type=int)
    parser.add_argument(
        "--hours",
        type=int,
        help="Explicit backfill window. Operational runs normally omit this.",
    )
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        summary = run_collector(
            args.config,
            args.sensor_index,
            args.hours,
            args.dry_run,
            reconcile=args.reconcile,
        )
    except PurpleAirCollectorError as exc:
        print(f"PurpleAir collector error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
