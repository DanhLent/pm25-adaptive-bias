from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.fetching import fetch_purpleair_realtime, fetch_purpleair_sensor_history, local_time_to_utc_epoch
from pm25_alert.data.loading import find_project_root, load_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["realtime", "history"], required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sensor-index", type=int)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--radius-km", type=float, default=5.0)
    parser.add_argument("--timezone")
    args = parser.parse_args()

    root = find_project_root()
    cfg = load_config(root / "config.yaml")
    source_cfg = cfg["data_sources"]
    pa_cfg = source_cfg["purpleair"]
    live_dir = root / source_cfg["incremental"]["raw_append_dir"]
    live_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get(pa_cfg["api_key_env"])
    fields = pa_cfg["fields"]

    if not api_key and not args.dry_run:
        print(f"PurpleAir API key is missing. Set {pa_cfg['api_key_env']} before live fetches.")
        return

    if args.mode == "realtime":
        loc = source_cfg["location"]
        df = fetch_purpleair_realtime(
            api_key=api_key,
            fields=fields,
            sensor_index=args.sensor_index,
            latitude=float(loc["latitude"]),
            longitude=float(loc["longitude"]),
            radius_km=args.radius_km,
            dry_run=args.dry_run,
        )
    else:
        if args.sensor_index is None or not args.start_date or not args.end_date:
            raise SystemExit("History mode requires --sensor-index, --start-date, and --end-date.")
        timezone_name = args.timezone or source_cfg["location"]["timezone"]
        df = fetch_purpleair_sensor_history(
            api_key=api_key,
            sensor_index=args.sensor_index,
            start_timestamp=local_time_to_utc_epoch(args.start_date, timezone_name),
            end_timestamp=local_time_to_utc_epoch(args.end_date, timezone_name),
            average_minutes=int(pa_cfg["default_average_minutes"]),
            fields=fields,
            dry_run=args.dry_run,
        )
    if args.dry_run:
        print(f"Dry run complete; returned rows={len(df)}")
        return
    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d_%H%M%S")
    out = live_dir / f"purpleair_{args.mode}_{stamp}.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out} rows={len(df)}")


if __name__ == "__main__":
    main()
