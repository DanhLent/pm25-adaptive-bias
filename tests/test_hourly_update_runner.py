from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(relative_path: str, name: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_legacy_hourly_entry_point_delegates_to_unified_runner():
    module = _load_module(
        "tools/data_collection/run_hourly_update.py",
        "run_hourly_update_compatibility",
    )
    args = module.build_arg_parser().parse_args([])

    assert args.config == "config.yaml"
    assert args.offline is False
    assert not hasattr(args, "hours")
    assert not hasattr(args, "sensor_index")


def test_due_calculation_is_timezone_aware_and_boundary_inclusive():
    module = _load_module(
        "tools/data_collection/run_unified_pipeline.py",
        "run_unified_pipeline_test",
    )
    now = datetime(2026, 7, 30, 16, 0, tzinfo=timezone.utc)

    assert module.is_due(None, now, timedelta(hours=24))
    assert not module.is_due("2026-07-29T16:00:01Z", now, timedelta(hours=24))
    assert module.is_due("2026-07-29T16:00:00Z", now, timedelta(hours=24))


def test_unified_dry_run_is_read_only(tmp_path, monkeypatch):
    module = _load_module(
        "tools/data_collection/run_unified_pipeline.py",
        "run_unified_pipeline_dry_run_test",
    )
    status_path = tmp_path / "must_not_exist.json"
    monkeypatch.setattr(module, "STATUS_PATH", status_path)

    return_code = module.main(
        [
            "--offline",
            "--dry-run",
            "--now",
            "2026-07-30T16:00:00Z",
        ]
    )

    assert return_code == 0
    assert not status_path.exists()
