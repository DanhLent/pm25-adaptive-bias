# Data Collection Tools

This folder contains host-side collection and refresh scripts for CAMS/Open-Meteo and PurpleAir data.

```bash
python tools/data_collection/07_fetch_openmeteo_cams.py --dry-run
python tools/data_collection/08_fetch_purpleair.py --mode realtime --dry-run
python tools/data_collection/08_fetch_purpleair.py --mode history --sensor-index SENSOR_ID --start-date 2026-05-14 --end-date 2026-05-20 --dry-run
python tools/data_collection/09_append_and_deduplicate.py
python tools/data_collection/10_run_incremental_update.py
python tools/data_collection/11_make_latest_snapshot.py
```

For live PurpleAir calls on Windows PowerShell:

```powershell
$env:PURPLEAIR_API_KEY="your_key_here"
python tools/data_collection/08_fetch_purpleair.py --mode realtime --sensor-index SENSOR_ID
```

The future scheduled PurpleAir collector plan is documented in `docs/data_collection/PURPLEAIR_COLLECTOR_PLAN.md`.
