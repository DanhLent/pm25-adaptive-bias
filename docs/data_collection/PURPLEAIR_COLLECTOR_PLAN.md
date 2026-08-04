# PurpleAir Collector Plan

The PurpleAir collector now supports the scheduled live-data path for this project.

## Goal

- Run once every 1 hour.
- Fetch the most recent 12-hour history window on each run.
- Backfill gaps caused by shutdown, sleep, or overnight downtime.
- Save raw API responses before normalization.
- Normalize history rows into a stable CSV schema.
- Append into a canonical live CSV.
- Deduplicate by `sensor_index + timestamp`.
- Keep the existing fusion, alert, RTL, and testbench behavior unchanged.

## Implemented Files

```text
tools/data_collection/purpleair_collector.py
data/live/purpleair/raw/
data/live/purpleair/normalized/
data/live/purpleair/logs/
data/live/purpleair/latest_run.json
data/live/purpleair/purpleair_live_hourly.csv
```

The collector reads PurpleAir settings from `data_sources.purpleair` in `config.yaml`.

## Config Shape

```yaml
data_sources:
  purpleair:
    api_base_url: "https://api.purpleair.com/v1"
    sensor_index: null
    api_key_env: "PURPLEAIR_API_KEY"
    default_average_minutes: 60
    backfill_hours: 12
    live_dir: "data/live/purpleair"
    canonical_live_csv: "data/live/purpleair/purpleair_live_hourly.csv"
```

`sensor_index` may remain `null` until the user knows which sensor to collect. Real collection requires either this config value or `--sensor-index`.

## Pipeline Link

`tools/data_collection/09_append_and_deduplicate.py` now prefers:

```text
data/live/purpleair/purpleair_live_hourly.csv
```

If the canonical file does not exist, it falls back to the older `data/live/*.csv` behavior.

The incremental runner can call the collector first:

```bash
python tools/data_collection/10_run_incremental_update.py --collect-purpleair
```

After collection, the existing append/dedup, dataset preparation, fusion, evaluation, figures, and latest snapshot steps run as before.

## Why 12 Hours

The collector is meant to run every 1 hour, but a laptop or workstation can sleep or shut down. Fetching the latest 12 hours each time makes the next run recover recent missing observations. Deduplication by `sensor_index + timestamp` keeps repeated windows from growing duplicate rows in the canonical live CSV.
