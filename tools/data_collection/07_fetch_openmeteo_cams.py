from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.fetching import fetch_openmeteo_cams_pm25
from pm25_alert.data.loading import (
    find_project_root,
    load_config,
    resolve_retry_backoff_seconds,
)


def _last_cams_date(root: Path) -> date | None:
    candidates = [
        root / "data/interim/cams_all_available.csv",
        root / "data/interim/cams_standardized.csv",
        root / "data/processed/pm25_fused_hourly_dataset.csv",
    ]
    for path in candidates:
        if path.exists():
            df = pd.read_csv(path, parse_dates=["time"])
            if "time" in df.columns and df["time"].notna().any():
                return pd.to_datetime(df["time"]).max().date()
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Re-fetch the most recent configured 72-hour window.",
    )
    args = parser.parse_args()

    root = find_project_root()
    cfg = load_config(root / "config.yaml")
    source_cfg = cfg["data_sources"]
    live_dir = root / source_cfg["incremental"]["raw_append_dir"]
    live_dir.mkdir(parents=True, exist_ok=True)

    last_date = _last_cams_date(root)
    if args.reconcile:
        reconciliation_hours = int(
            source_cfg["openmeteo"].get("reconciliation_hours", 72)
        )
        default_start = (
            date.today() - timedelta(days=max(1, reconciliation_hours // 24))
        ).isoformat()
    elif last_date:
        overlap_days = int(source_cfg["openmeteo"].get("incremental_overlap_days", 1))
        default_start = (last_date - timedelta(days=overlap_days)).isoformat()
    else:
        default_start = source_cfg["openmeteo"]["default_start_date"]
    start_date = args.start_date or default_start
    end_date = args.end_date or date.today().isoformat()
    if start_date > end_date:
        if args.dry_run:
            start_date = end_date
        else:
            print(f"No missing Open-Meteo date range to fetch: start_date={start_date}, end_date={end_date}")
            return

    loc = source_cfg["location"]
    df = fetch_openmeteo_cams_pm25(
        latitude=float(loc["latitude"]),
        longitude=float(loc["longitude"]),
        start_date=start_date,
        end_date=end_date,
        timezone=loc["timezone"],
        domain=source_cfg["openmeteo"]["domain"],
        dry_run=args.dry_run,
        retry_backoff_seconds=resolve_retry_backoff_seconds(cfg),
    )
    if args.dry_run:
        print(f"Dry run complete; returned rows={len(df)}")
        return
    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d_%H%M%S")
    out = live_dir / f"openmeteo_cams_pm25_increment_{stamp}.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out} rows={len(df)}")


if __name__ == "__main__":
    main()
