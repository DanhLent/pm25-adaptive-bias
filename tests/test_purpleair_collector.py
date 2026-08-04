from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_collector_module():
    path = ROOT / "tools" / "data_collection" / "purpleair_collector.py"
    spec = importlib.util.spec_from_file_location("purpleair_collector", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_normalize_history_payload_schema_and_values():
    module = _load_collector_module()
    payload = {
        "fields": ["time_stamp", "pm2.5_cf_1", "pm2.5_cf_1_a", "pm2.5_cf_1_b", "pm2.5_atm", "humidity", "temperature"],
        "data": [
            [1770000000, 12.5, 12.0, 13.0, 12.8, 66.0, 30.5],
            [1770003600, None, 14.0, 16.0, 15.2, None, None],
        ],
    }

    df = module.normalize_history_payload(payload, sensor_index=12345, raw_source="raw.json", fetch_time_utc="2026-07-01T00:00:00Z")

    assert list(df.columns) == module.NORMALIZED_COLUMNS
    assert len(df) == 2
    assert df["sensor_index"].tolist() == [12345, 12345]
    assert df["timestamp"].str.endswith("Z").all()
    assert df["pm25"].tolist() == [12.5, 15.2]
    assert df["raw_source"].tolist() == ["raw.json", "raw.json"]


def test_append_canonical_deduplicates_sensor_timestamp(tmp_path):
    module = _load_collector_module()
    canonical = tmp_path / "purpleair_live_hourly.csv"
    first = pd.DataFrame(
        {
            "timestamp": ["2026-07-01T00:00:00Z", "2026-07-01T01:00:00Z"],
            "time": ["2026-07-01T00:00:00Z", "2026-07-01T01:00:00Z"],
            "sensor_index": [12345, 12345],
            "pm25": [10.0, 11.0],
        }
    )
    second = pd.DataFrame(
        {
            "timestamp": ["2026-07-01T01:00:00Z", "2026-07-01T02:00:00Z"],
            "time": ["2026-07-01T01:00:00Z", "2026-07-01T02:00:00Z"],
            "sensor_index": [12345, 12345],
            "pm25": [12.0, 13.0],
        }
    )

    module.append_canonical(canonical, first)
    combined, duplicates_removed = module.append_canonical(canonical, second)

    assert duplicates_removed == 1
    assert len(combined) == 3
    assert combined.loc[combined["timestamp"] == "2026-07-01T01:00:00Z", "pm25"].iloc[0] == 12.0
    assert canonical.exists()


def test_missing_sensor_index_reports_clear_error():
    module = _load_collector_module()
    with pytest.raises(module.PurpleAirCollectorError, match="sensor_index is missing"):
        module.resolve_sensor_index({"sensor_index": None}, cli_sensor_index=None, require=True)


def test_missing_api_key_reports_clear_error(monkeypatch):
    module = _load_collector_module()
    monkeypatch.delenv("PURPLEAIR_API_KEY", raising=False)
    with pytest.raises(module.PurpleAirCollectorError, match="PURPLEAIR_API_KEY"):
        module.resolve_api_key({"api_key_env": "PURPLEAIR_API_KEY"}, require=True)


def test_run_collector_logs_missing_api_key(tmp_path, monkeypatch):
    module = _load_collector_module()
    monkeypatch.delenv("PURPLEAIR_API_KEY", raising=False)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
data_sources:
  purpleair:
    api_base_url: "https://api.purpleair.com/v1"
    sensor_index: 12345
    api_key_env: "PURPLEAIR_API_KEY"
    default_average_minutes: 60
    backfill_hours: 12
    live_dir: "data/live/purpleair"
    canonical_live_csv: "data/live/purpleair/purpleair_live_hourly.csv"
    fields: ["pm2.5_cf_1"]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(module.PurpleAirCollectorError, match="PURPLEAIR_API_KEY"):
        module.run_collector(config_path=config_path, dry_run=False)

    latest_run = json.loads((tmp_path / "data" / "live" / "purpleair" / "latest_run.json").read_text(encoding="utf-8"))
    assert latest_run["status"] == "error"
    assert "PURPLEAIR_API_KEY" in latest_run["error"]


def test_operations_retry_backoff_is_passed_to_history_fetch(
    tmp_path,
    monkeypatch,
):
    module = _load_collector_module()
    monkeypatch.setenv("PURPLEAIR_API_KEY", "unit-test-key")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
project:
  timezone: "Asia/Ho_Chi_Minh"
operations:
  retry_backoff_seconds: [1, 7]
data_sources:
  purpleair:
    api_base_url: "https://api.purpleair.com/v1"
    sensor_index: 12345
    api_key_env: "PURPLEAIR_API_KEY"
    default_average_minutes: 10
    initial_lookback_hours: 72
    incremental_overlap_hours: 2
    reconciliation_hours: 72
    live_dir: "data/live/purpleair"
    canonical_live_csv: "data/live/purpleair/purpleair_10min.csv"
    fields: ["pm2.5_cf_1"]
""".strip(),
        encoding="utf-8",
    )
    captured: dict[str, tuple[int, ...]] = {}

    def fake_fetch(
        api_key,
        sensor_index,
        pa_cfg,
        start,
        end,
        retry_backoff_seconds,
    ):
        assert api_key == "unit-test-key"
        assert sensor_index == 12345
        captured["backoffs"] = retry_backoff_seconds
        return {
            "fields": ["time_stamp", "pm2.5_cf_1"],
            "data": [[1770000000, 12.5]],
        }

    monkeypatch.setattr(module, "fetch_history_payload", fake_fetch)

    summary = module.run_collector(config_path=config_path)

    assert captured["backoffs"] == (1, 7)
    assert summary["retry_backoff_seconds"] == [1, 7]


@pytest.mark.parametrize(
    "values",
    [
        [-1],
        [True],
        [1.5],
        list(range(9)),
    ],
)
def test_retry_backoff_validation_rejects_invalid_values(values):
    from pm25_alert.data.loading import resolve_retry_backoff_seconds

    with pytest.raises(ValueError, match="retry_backoff_seconds"):
        resolve_retry_backoff_seconds(
            {"operations": {"retry_backoff_seconds": values}}
        )
