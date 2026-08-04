from __future__ import annotations

import os
import math
import time
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from pm25_alert.data.loading import resolve_retry_backoff_seconds

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None


OPENMETEO_COLUMNS = ["time", "cams_pm25", "source", "fetch_time_utc", "latitude", "longitude", "domain"]
PURPLEAIR_REALTIME_COLUMNS = ["time", "source", "fetch_time_utc", "sensor_index", "latitude", "longitude"]
PURPLEAIR_HISTORY_COLUMNS = ["time", "source", "fetch_time_utc", "sensor_index"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_requests() -> Any:
    if requests is None:
        raise RuntimeError("The `requests` package is required for live API calls. Install requirements.txt first.")
    return requests


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def compute_bounding_box(latitude: float, longitude: float, radius_km: float) -> dict[str, float]:
    delta_lat = radius_km / 111.0
    cos_lat = max(abs(math.cos(math.radians(latitude))), 1e-6)
    delta_lon = radius_km / (111.0 * cos_lat)
    return {
        "nwlat": latitude + delta_lat,
        "nwlng": longitude - delta_lon,
        "selat": latitude - delta_lat,
        "selng": longitude + delta_lon,
    }


def local_time_to_utc_epoch(value: str, timezone_name: str = "Asia/Ho_Chi_Minh") -> int:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize(ZoneInfo(timezone_name))
    else:
        ts = ts.tz_convert("UTC")
    return int(ts.tz_convert("UTC").timestamp())


def _haversine_km(lat1: float, lon1: float, lat2: pd.Series, lon2: pd.Series) -> pd.Series:
    r = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = pd.to_numeric(lat2, errors="coerce").map(math.radians)
    lon2_rad = pd.to_numeric(lon2, errors="coerce").map(math.radians)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (dlat / 2).map(math.sin) ** 2 + math.cos(lat1_rad) * lat2_rad.map(math.cos) * (dlon / 2).map(math.sin) ** 2
    return 2 * r * a.map(lambda x: math.asin(min(1.0, math.sqrt(x))) if not pd.isna(x) else math.nan)


def fetch_openmeteo_cams_pm25(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    timezone: str = "Asia/Ho_Chi_Minh",
    domain: str = "cams_global",
    dry_run: bool = False,
    retry_backoff_seconds: tuple[int, ...] | None = None,
) -> pd.DataFrame:
    base_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "pm2_5",
        "timezone": timezone,
        "domains": domain,
    }
    if dry_run:
        print(f"DRY RUN Open-Meteo GET {base_url} params={params}")
        return _empty_frame(OPENMETEO_COLUMNS)
    retry_backoffs = resolve_retry_backoff_seconds(
        {
            "operations": {
                "retry_backoff_seconds": (
                    list(retry_backoff_seconds)
                    if retry_backoff_seconds is not None
                    else None
                )
            }
        }
    )
    req = _require_requests()
    payload = None
    failure = "unknown failure"
    for attempt in range(len(retry_backoffs) + 1):
        try:
            response = req.get(base_url, params=params, timeout=30)
            if response.ok:
                payload = response.json()
                break
            transient = response.status_code in {408, 425, 429} or response.status_code >= 500
            if not transient:
                raise RuntimeError(
                    f"Open-Meteo request failed with non-transient HTTP {response.status_code}."
                )
            failure = f"transient HTTP {response.status_code}"
        except RuntimeError:
            raise
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
        if attempt >= len(retry_backoffs):
            raise RuntimeError(
                f"Open-Meteo request failed after bounded retries ({failure})."
            )
        time.sleep(retry_backoffs[attempt])
    if not isinstance(payload, dict):
        raise RuntimeError("Open-Meteo response was not a JSON object.")
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    pm25 = hourly.get("pm2_5", [])
    df = pd.DataFrame({"time": times, "cams_pm25": pm25})
    df["source"] = "openmeteo_cams"
    df["fetch_time_utc"] = _utc_now_iso()
    df["latitude"] = latitude
    df["longitude"] = longitude
    df["domain"] = domain
    return df


def fetch_purpleair_realtime(
    api_key: str | None,
    fields: list[str],
    sensor_index: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    dry_run: bool = False,
) -> pd.DataFrame:
    api_key = api_key or os.environ.get("PURPLEAIR_API_KEY")
    fields_for_request = list(dict.fromkeys([*fields, "latitude", "longitude"]))
    if sensor_index is not None:
        base_url = f"https://api.purpleair.com/v1/sensors/{sensor_index}"
        params: dict[str, Any] = {"fields": ",".join(fields_for_request)}
    else:
        base_url = "https://api.purpleair.com/v1/sensors"
        params = {"fields": ",".join(fields_for_request), "location_type": 0}
        if latitude is not None and longitude is not None and radius_km is not None:
            params.update(compute_bounding_box(latitude, longitude, radius_km))
    columns = [*PURPLEAIR_REALTIME_COLUMNS, *fields_for_request]
    if dry_run:
        print(f"DRY RUN PurpleAir realtime GET {base_url} params={params}; api_key_set={bool(api_key)}")
        return _empty_frame(columns)
    if not api_key:
        raise ValueError("PurpleAir API key is missing. Set PURPLEAIR_API_KEY or pass api_key explicitly.")
    req = _require_requests()
    response = req.get(base_url, params=params, headers={"X-API-Key": api_key}, timeout=30)
    if not response.ok:
        raise RuntimeError(f"PurpleAir realtime request failed: HTTP {response.status_code}: {response.text[:300]}")
    payload = response.json()
    if "sensor" in payload:
        df = pd.DataFrame([payload["sensor"]])
    else:
        data = payload.get("data", [])
        cols = payload.get("fields", [])
        df = pd.DataFrame(data, columns=cols)
    if "last_seen" in df.columns:
        df["time"] = pd.to_datetime(df["last_seen"], unit="s", utc=True, errors="coerce")
    else:
        df["time"] = pd.Timestamp.now(tz="UTC")
    df["source"] = "purpleair_realtime"
    df["fetch_time_utc"] = _utc_now_iso()
    if sensor_index is not None:
        df["sensor_index"] = sensor_index
    elif "sensor_index" not in df.columns and "sensor" in df.columns:
        df["sensor_index"] = df["sensor"]
    if latitude is not None and longitude is not None and {"latitude", "longitude"}.issubset(df.columns):
        df["distance_km_from_target"] = _haversine_km(latitude, longitude, df["latitude"], df["longitude"])
        df = df.sort_values("distance_km_from_target").reset_index(drop=True)
    return df


def fetch_purpleair_sensor_history(
    api_key: str | None,
    sensor_index: int,
    start_timestamp: int,
    end_timestamp: int,
    average_minutes: int = 10,
    fields: list[str] | None = None,
    dry_run: bool = False,
) -> pd.DataFrame:
    api_key = api_key or os.environ.get("PURPLEAIR_API_KEY")
    fields = fields or ["pm2.5_cf_1", "pm2.5_cf_1_a", "pm2.5_cf_1_b"]
    base_url = f"https://api.purpleair.com/v1/sensors/{sensor_index}/history"
    params = {
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "average": average_minutes,
        "fields": ",".join(fields),
    }
    columns = [*PURPLEAIR_HISTORY_COLUMNS, *fields]
    if dry_run:
        print(f"DRY RUN PurpleAir history GET {base_url} params={params}; api_key_set={bool(api_key)}")
        return _empty_frame(columns)
    if not api_key:
        raise ValueError("PurpleAir API key is missing. Set PURPLEAIR_API_KEY or pass api_key explicitly.")
    req = _require_requests()
    response = req.get(base_url, params=params, headers={"X-API-Key": api_key}, timeout=60)
    if not response.ok:
        raise RuntimeError(f"PurpleAir history request failed: HTTP {response.status_code}: {response.text[:300]}")
    payload = response.json()
    data = payload.get("data", [])
    cols = payload.get("fields", [])
    df = pd.DataFrame(data, columns=cols)
    if "time_stamp" in df.columns:
        df["time"] = pd.to_datetime(df["time_stamp"], unit="s", utc=True, errors="coerce")
    df["source"] = "purpleair_history"
    df["fetch_time_utc"] = _utc_now_iso()
    df["sensor_index"] = sensor_index
    return df
