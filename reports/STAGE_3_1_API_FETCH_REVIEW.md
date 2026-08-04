# Stage 3.1 API Fetch Review

## What Changed

Stage 3.1 hardened the API fetch layer without changing the Stage 2 fusion algorithm and without starting Stage 4.

- PurpleAir realtime now supports exact sensor fetches with `GET /v1/sensors/{sensor_index}`.
- PurpleAir nearby realtime search now uses bounding-box parameters instead of `lat`, `lon`, and `max_distance`.
- PurpleAir history date strings are interpreted in the project timezone by default before conversion to UTC epoch seconds.
- Dry-run output now shows the final endpoint and request parameters.
- Tests now validate request construction without live internet calls.

## Exact Sensor Realtime Mode

Command:

```bash
python tools/data_collection/08_fetch_purpleair.py --mode realtime --sensor-index SENSOR_ID
```

This calls `/v1/sensors/{sensor_index}` and handles responses where data are nested under `sensor`. The output includes `time`, `source`, `fetch_time_utc`, `sensor_index`, and requested PurpleAir fields when present.

## Nearby Sensor Search

Command:

```bash
python tools/data_collection/08_fetch_purpleair.py --mode realtime --radius-km 5
```

The script computes:

```text
delta_lat = radius_km / 111.0
delta_lon = radius_km / (111.0 * cos(latitude_rad))
```

It sends `nwlat`, `nwlng`, `selat`, `selng`, `location_type`, and `fields` to `/v1/sensors`. If returned latitude/longitude columns exist, it computes `distance_km_from_target` and sorts by distance.

## Local-Time History Conversion

History command:

```bash
python tools/data_collection/08_fetch_purpleair.py --mode history --sensor-index SENSOR_ID --start-date 2026-05-14 --end-date 2026-05-20
```

Date-only strings are interpreted as local midnight in `Asia/Ho_Chi_Minh` unless `--timezone` is provided. For example, `2026-05-14` becomes `2026-05-13 17:00:00 UTC` before conversion to epoch seconds.

## Dry Runs Tested

```bash
python tools/data_collection/07_fetch_openmeteo_cams.py --dry-run
python tools/data_collection/08_fetch_purpleair.py --mode realtime --dry-run
python tools/data_collection/08_fetch_purpleair.py --mode realtime --sensor-index 12345 --dry-run
python tools/data_collection/08_fetch_purpleair.py --mode history --sensor-index 12345 --start-date 2026-05-14 --end-date 2026-05-20 --dry-run
```

All dry-run commands succeeded without API keys.

## Tests Passed

`python -m pytest tests -q` passed with 16 tests.

The tests verify:

- Open-Meteo request parameter construction.
- PurpleAir nearby realtime bounding-box parameters.
- PurpleAir exact sensor endpoint construction.
- PurpleAir history local-time to UTC epoch conversion.
- Dry-run DataFrame structures.
- Append/deduplication behavior.
- Latest snapshot generation.

## Remaining Limits

The system remains proof-of-concept because PurpleAir history is short and A/B channel disagreement is high. Stage 3.1 improves data acquisition readiness; it does not validate an operational warning system and does not add online ML.

## Freeze Decision

Stage 3 can now be frozen as the data collection and incremental-update foundation. Stage 4 should not begin until more PurpleAir history has accumulated.
