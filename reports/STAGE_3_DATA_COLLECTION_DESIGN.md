# Stage 3 Data Collection Design

## Objective

Stage 3 builds the data accumulation and incremental-update foundation needed before any credible self-learning work. The current PurpleAir overlap is too short for reliable ML, so the technically correct next step is to collect, append, deduplicate, and reprocess more data reproducibly.

## Why Data Accumulation Comes First

The existing CAMS/Open-Meteo record is long, but the local PurpleAir overlap is only about 49 hourly rows. Future self-learning needs a longer local residual history before any model comparison or online adaptation can be trusted.

## Why Not Deep Learning Yet

Deep learning is not appropriate for the current dataset. Stage 3 does not add LSTM, Transformer, or other complex model families. It prepares clean incremental data streams so future lightweight models can be evaluated honestly.

## Open-Meteo Fetching

`tools/data_collection/07_fetch_openmeteo_cams.py` uses `src/pm25_alert/data/fetching.py` to fetch hourly CAMS PM2.5 from Open-Meteo. It supports dry-run mode, explicit start/end dates, and timestamped append-only CSV outputs under `data/live/`.

## PurpleAir Fetching

`tools/data_collection/08_fetch_purpleair.py` supports realtime and history modes. It reads the PurpleAir API key from `PURPLEAIR_API_KEY`; dry-run mode works without a key and does not call the internet.

Realtime mode has two paths. If `--sensor-index` is supplied, the script calls the exact sensor endpoint `/v1/sensors/{sensor_index}`. If no sensor index is supplied, it performs nearby search using a bounding box computed from configured latitude/longitude and `--radius-km`; returned sensors are sorted by distance when latitude/longitude columns are present.

History mode treats `--start-date` and `--end-date` as local project-time values by default. Date-only strings are local midnight in `Asia/Ho_Chi_Minh`, then converted to UTC epoch seconds for PurpleAir. Timezone-aware timestamps preserve their meaning and are converted to UTC.

## Append-Only Raw Preservation

New fetched files are never written over the original CSV files. Each fetch creates a timestamped file in `data/live/`. The original project-root CSVs and `data/raw/` copies remain unchanged.

## Deduplication

`tools/data_collection/09_append_and_deduplicate.py` reads `data/raw/` and `data/live/`, standardizes timestamps, sorts records, and writes canonical all-available datasets:

- `data/interim/cams_all_available.csv`
- `data/interim/purpleair_all_available.csv`

Duplicates are removed by timestamp and source-specific identifiers when present. A report is written to `reports/STAGE_3_APPEND_DEDUP_REPORT.md`.

## Incremental Update

`tools/data_collection/10_run_incremental_update.py` orchestrates append/deduplication, preprocessing, Stage 2 fusion, Stage 2 evaluation, Stage 2 figures, and latest snapshot generation. It writes a run log to `reports/STAGE_3_STATUS.md`.

## Latest Snapshot

`tools/data_collection/11_make_latest_snapshot.py` reads the fusion timeline and creates:

- `outputs/latest/latest_fusion_alert_snapshot.csv`
- `outputs/latest/latest_alert_summary.json`

These files are useful for demos, dashboards, and future embedded-system handoff.

## Self-Learning Readiness

Stage 3 creates the repeatable data loop needed for future self-learning hooks. It does not implement online ML yet. Once enough PurpleAir history accumulates, Stage 4 or later work can compare lightweight learning approaches against EMA and Dual-EMA baselines.
