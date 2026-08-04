from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.loading import load_config
from pm25_alert.data.preparation import prepare_canonical_data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import, QC, aggregate, and CAMS-left-join canonical PM2.5 data."
    )
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    summary = prepare_canonical_data(ROOT, load_config(config_path))
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
