from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.hardware import process_hardware_timeline
from pm25_alert.data.loading import load_config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the bit-exact hardware-aligned PM2.5 timeline."
    )
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    config = load_config(config_path)
    hardware = config["hardware_aligned"]
    input_path = ROOT / hardware["hourly_input_csv"]
    if not input_path.exists():
        raise FileNotFoundError(
            f"Canonical hourly input is missing: {input_path}. "
            "Run tools/data_collection/prepare_canonical_data.py first."
        )
    summary = process_hardware_timeline(
        pd.read_csv(input_path),
        config=config,
        trace_path=ROOT / hardware["trace_csv"],
        state_path=ROOT / hardware["state_json"],
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
