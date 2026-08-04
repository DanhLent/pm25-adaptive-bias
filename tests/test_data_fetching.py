from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data import fetching as data_fetching
from pm25_alert.data.fetching import (
    fetch_openmeteo_cams_pm25,
    fetch_purpleair_realtime,
    fetch_purpleair_sensor_history,
    local_time_to_utc_epoch,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.ok = True
        self.status_code = 200
        self.text = ""

    def json(self):
        return self.payload


class FakeRequests:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return FakeResponse(self.payload)


def _load_append_module():
    path = ROOT / "tools" / "data_collection" / "09_append_and_deduplicate.py"
    spec = importlib.util.spec_from_file_location("append_dedup", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_openmeteo_dry_run_structure():
    df = fetch_openmeteo_cams_pm25(10.879, 106.806, "2026-05-14", "2026-05-14", dry_run=True)
    assert {"time", "cams_pm25", "source", "fetch_time_utc"}.issubset(df.columns)
    assert df.empty


def test_openmeteo_fetch_constructs_expected_params():
    fake = FakeRequests({"hourly": {"time": ["2026-05-14T00:00"], "pm2_5": [12.3]}})
    old_requests = data_fetching.requests
    data_fetching.requests = fake
    try:
        df = fetch_openmeteo_cams_pm25(10.879, 106.806, "2026-05-14", "2026-05-15", dry_run=False)
    finally:
        data_fetching.requests = old_requests
    call = fake.calls[0]
    assert call["params"]["latitude"] == 10.879
    assert call["params"]["longitude"] == 106.806
    assert call["params"]["hourly"] == "pm2_5"
    assert len(df) == 1


def test_purpleair_missing_key_dry_run_structure():
    df = fetch_purpleair_realtime(None, ["pm2.5_cf_1"], latitude=10.879, longitude=106.806, radius_km=5, dry_run=True)
    assert {"time", "source", "fetch_time_utc", "pm2.5_cf_1"}.issubset(df.columns)
    assert df.empty


def test_purpleair_nearby_uses_bounding_box_params():
    fake = FakeRequests({"fields": ["sensor_index", "latitude", "longitude", "pm2.5_cf_1"], "data": [[1, 10.88, 106.81, 12.0]]})
    old_requests = data_fetching.requests
    data_fetching.requests = fake
    try:
        df = fetch_purpleair_realtime("key", ["pm2.5_cf_1"], latitude=10.879, longitude=106.806, radius_km=5, dry_run=False)
    finally:
        data_fetching.requests = old_requests
    params = fake.calls[0]["params"]
    assert {"nwlat", "nwlng", "selat", "selng"}.issubset(params)
    assert "max_distance" not in params
    assert "lat" not in params
    assert "lon" not in params
    assert "distance_km_from_target" in df.columns


def test_purpleair_exact_sensor_uses_sensor_endpoint():
    fake = FakeRequests({"sensor": {"sensor_index": 12345, "pm2.5_cf_1": 11.0, "latitude": 10.879, "longitude": 106.806}})
    old_requests = data_fetching.requests
    data_fetching.requests = fake
    try:
        df = fetch_purpleair_realtime("key", ["pm2.5_cf_1"], sensor_index=12345, dry_run=False)
    finally:
        data_fetching.requests = old_requests
    assert fake.calls[0]["url"].endswith("/v1/sensors/12345")
    assert len(df) == 1
    assert int(df["sensor_index"].iloc[0]) == 12345


def test_purpleair_history_local_dates_to_utc_epoch_and_params():
    start = local_time_to_utc_epoch("2026-05-14", "Asia/Ho_Chi_Minh")
    end = local_time_to_utc_epoch("2026-05-20", "Asia/Ho_Chi_Minh")
    assert pd.Timestamp(start, unit="s", tz="UTC").isoformat() == "2026-05-13T17:00:00+00:00"
    fake = FakeRequests({"fields": ["time_stamp", "pm2.5_cf_1"], "data": [[start, 10.0]]})
    old_requests = data_fetching.requests
    data_fetching.requests = fake
    try:
        df = fetch_purpleair_sensor_history("key", 12345, start, end, dry_run=False)
    finally:
        data_fetching.requests = old_requests
    assert fake.calls[0]["url"].endswith("/v1/sensors/12345/history")
    assert fake.calls[0]["params"]["start_timestamp"] == start
    assert fake.calls[0]["params"]["end_timestamp"] == end
    assert len(df) == 1


def test_append_deduplicate_handles_duplicates():
    module = _load_append_module()
    df = pd.DataFrame({"time": ["2026-05-14 00:00", "2026-05-14 00:00", "2026-05-14 01:00"], "value": [1, 2, 3]})
    deduped, duplicate_count = module.deduplicate_by_time(df)
    assert duplicate_count == 1
    assert len(deduped) == 2
    assert deduped.loc[deduped["time"] == "2026-05-14 00:00", "value"].iloc[0] == 2


if __name__ == "__main__":
    test_openmeteo_dry_run_structure()
    test_openmeteo_fetch_constructs_expected_params()
    test_purpleair_missing_key_dry_run_structure()
    test_purpleair_nearby_uses_bounding_box_params()
    test_purpleair_exact_sensor_uses_sensor_endpoint()
    test_purpleair_history_local_dates_to_utc_epoch_and_params()
    test_append_deduplicate_handles_duplicates()
    print("data_fetching tests passed")
