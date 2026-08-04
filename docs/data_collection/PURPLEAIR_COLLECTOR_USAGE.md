# PurpleAir 10-Minute Collector

The collector maintains one canonical append-only product:

```text
data/live/purpleair/purpleair_10min.csv
```

Rows are uniquely identified by sensor index, UTC timestamp, PM2.5 product, and averaging resolution. Writes to raw batches, normalized batches, canonical CSV, state, and run status use staging plus atomic replacement.

## Credential and sensor

The API key is read from `PURPLEAIR_API_KEY`; it is never accepted in config or logged:

```powershell
$env:PURPLEAIR_API_KEY = "REPLACE_ME"
```

The reviewed sensor index is configured under `data_sources.purpleair.sensor_index` in `config.yaml`. `--sensor-index` is an explicit override.

## Normal operation

Preview the request without network writes:

```powershell
.\.venv\Scripts\python.exe .\tools\data_collection\purpleair_collector.py `
  --config .\config.yaml --dry-run
```

Run incrementally:

```powershell
.\.venv\Scripts\python.exe .\tools\data_collection\purpleair_collector.py `
  --config .\config.yaml
```

The initial run looks back 72 hours. Later runs start from the last successful raw timestamp minus a two-hour overlap. Canonical deduplication makes overlap safe and allows recent gaps to be repaired.

Daily reconciliation explicitly re-fetches the most recent 72 hours:

```powershell
.\.venv\Scripts\python.exe .\tools\data_collection\purpleair_collector.py `
  --config .\config.yaml --reconcile
```

`--hours N` is an explicit operator backfill override. It is not the hourly default:

```powershell
.\.venv\Scripts\python.exe .\tools\data_collection\purpleair_collector.py `
  --config .\config.yaml --hours 168
```

Use the unified orchestrator for scheduled work. The legacy incremental/hourly entry points delegate to it:

```powershell
.\.venv\Scripts\python.exe .\tools\data_collection\run_unified_pipeline.py --dry-run
```

## Outputs

```text
data/live/purpleair/raw/
data/live/purpleair/normalized/
data/live/purpleair/purpleair_10min.csv
data/live/purpleair/latest_run.json
```

The raw and normalized batch files retain source/provenance details. The canonical file records schema version, collection timestamp, source file/hash, sensor/product/resolution identity, official aggregate and A/B fields, and environmental fields when supplied.

Transient API failures use the single bounded policy in
`operations.retry_backoff_seconds` (currently 30, 60, and 120 seconds), then
fail. The same policy is passed explicitly to PurpleAir and CAMS collection;
source-specific blocks do not shadow it. Values must be a bounded list of
nonnegative integers. Authentication, validation, and schema errors fail
immediately. Failure never advances the successful timestamp.
