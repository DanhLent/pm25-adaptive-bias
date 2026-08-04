# Stage 3 Runbook

## Dry Run API Calls

```bash
python tools/data_collection/07_fetch_openmeteo_cams.py --dry-run
python tools/data_collection/08_fetch_purpleair.py --mode realtime --dry-run
python tools/data_collection/08_fetch_purpleair.py --mode realtime --sensor-index SENSOR_ID --dry-run
python tools/data_collection/08_fetch_purpleair.py --mode history --sensor-index SENSOR_ID --start-date 2026-05-14 --end-date 2026-05-20 --dry-run
```

Dry-run mode does not call the internet and does not require API keys.

## Fetch Open-Meteo CAMS for a Date Range

```bash
python tools/data_collection/07_fetch_openmeteo_cams.py --start-date 2026-05-15 --end-date 2026-05-20
```

Outputs are written append-only under `data/live/`.

## PurpleAir Realtime Fetch

Nearby search uses a bounding box derived from configured latitude/longitude and `--radius-km`. It sends `nwlat`, `nwlng`, `selat`, and `selng` to `/v1/sensors`, then sorts by distance when returned latitude/longitude are available.

Windows PowerShell:

```powershell
$env:PURPLEAIR_API_KEY="your_key_here"
python tools/data_collection/08_fetch_purpleair.py --mode realtime
```

macOS/Linux:

```bash
export PURPLEAIR_API_KEY="your_key_here"
python tools/data_collection/08_fetch_purpleair.py --mode realtime
```

## PurpleAir Exact Sensor Realtime Fetch

Use this when you know the PurpleAir sensor index. It calls `/v1/sensors/{sensor_index}` and returns a single sensor row when possible.

Windows PowerShell:

```powershell
$env:PURPLEAIR_API_KEY="your_key_here"
python tools/data_collection/08_fetch_purpleair.py --mode realtime --sensor-index SENSOR_ID
```

## PurpleAir History Fetch

```bash
python tools/data_collection/08_fetch_purpleair.py --mode history --sensor-index SENSOR_ID --start-date 2026-05-14 --end-date 2026-05-20
```

`--start-date` and `--end-date` are interpreted in the project timezone (`Asia/Ho_Chi_Minh`) unless `--timezone` is passed. Date-only strings mean local midnight, then the script converts to UTC epoch seconds before calling PurpleAir.

```bash
python tools/data_collection/08_fetch_purpleair.py --mode history --sensor-index SENSOR_ID --start-date 2026-05-14 --end-date 2026-05-20 --timezone Asia/Ho_Chi_Minh
```

## Run Local Incremental Update Only

```bash
python tools/data_collection/10_run_incremental_update.py
```

This uses local `data/raw/` and `data/live/` files. It does not require API keys.

## Latest Snapshot

```bash
python tools/data_collection/11_make_latest_snapshot.py
```

Outputs:

- `outputs/latest/latest_fusion_alert_snapshot.csv`
- `outputs/latest/latest_alert_summary.json`

## Scheduling Note

For recurring operation, use Windows Task Scheduler or cron conceptually to run fetch and incremental update commands. This project does not create scheduled OS tasks automatically.
