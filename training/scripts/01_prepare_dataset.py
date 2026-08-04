from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.data.loading import load_config
from pm25_alert.data.preparation import prepare_canonical_data


def main() -> None:
    """Compatibility entry point for the canonical CAMS-led preparation flow."""
    config = load_config(ROOT / "config.yaml")
    summary = prepare_canonical_data(ROOT, config)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
