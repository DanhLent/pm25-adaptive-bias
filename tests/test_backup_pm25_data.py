from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_backup_module():
    path = ROOT / "tools" / "backup" / "backup_pm25_data.py"
    spec = importlib.util.spec_from_file_location("backup_pm25_data", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_backup_copies_allowlisted_files_and_skips_forbidden_paths(tmp_path, monkeypatch):
    module = _load_backup_module()
    project = tmp_path / "project"
    dest = tmp_path / "drive"
    project.mkdir()
    dest.mkdir()

    (project / "data" / "interim").mkdir(parents=True)
    (project / "data" / "interim" / "purpleair_hourly.csv").write_text(
        "timestamp,pm25\n2026-07-01T00:00:00Z,12.3\n",
        encoding="utf-8",
    )
    (project / "data" / "interim" / "__pycache__").mkdir()
    (project / "data" / "interim" / "__pycache__" / "bad.pyc").write_bytes(b"cache")
    (project / "scripts" / "windows").mkdir(parents=True)
    (project / "scripts" / "windows" / "run_pm25_hourly_update.bat").write_text(
        "set PURPLEAIR_API_KEY=secret\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        module,
        "BACKUP_SOURCES",
        (
            "data/interim",
            "scripts/windows/run_pm25_hourly_update.bat",
        ),
    )

    exit_code, manifest, manifest_path = module.run_backup(
        project_root=project,
        dest_root=dest,
        no_snapshot=True,
        now=datetime(2026, 7, 1, 8, 30, tzinfo=timezone.utc),
    )

    assert exit_code == 0
    assert manifest["status"] == "ok"
    assert manifest["latest_updated"] is True
    assert (dest / "latest" / "data" / "interim" / "purpleair_hourly.csv").exists()
    assert not (dest / "latest" / "data" / "interim" / "__pycache__").exists()
    assert not (
        dest / "latest" / "scripts" / "windows" / "run_pm25_hourly_update.bat"
    ).exists()

    loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    skipped_paths = {item["path"] for item in loaded_manifest["skipped"]}
    assert "data/interim/__pycache__/bad.pyc" in skipped_paths
    assert "scripts/windows/run_pm25_hourly_update.bat" in skipped_paths
    assert loaded_manifest["summary"]["files_copied"] == 1


def test_backup_retention_removes_snapshots_older_than_keep_days(tmp_path, monkeypatch):
    module = _load_backup_module()
    project = tmp_path / "project"
    dest = tmp_path / "drive"
    snapshots = dest / "snapshots"
    project.mkdir()
    snapshots.mkdir(parents=True)
    (project / "config.yaml").write_text("project: pm25\n", encoding="utf-8")

    old_snapshot = snapshots / "pm25_backup_20260501_000000.zip"
    old_snapshot.write_bytes(b"old")
    old_time = datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp()
    os.utime(old_snapshot, (old_time, old_time))

    recent_snapshot = snapshots / "pm25_backup_20260629_000000.zip"
    recent_snapshot.write_bytes(b"recent")
    recent_time = datetime(2026, 6, 29, tzinfo=timezone.utc).timestamp()
    os.utime(recent_snapshot, (recent_time, recent_time))

    monkeypatch.setattr(module, "BACKUP_SOURCES", ("config.yaml",))

    exit_code, manifest, _ = module.run_backup(
        project_root=project,
        dest_root=dest,
        no_snapshot=True,
        keep_days=30,
        now=datetime(2026, 7, 1, tzinfo=timezone.utc) + timedelta(hours=12),
    )

    assert exit_code == 0
    assert not old_snapshot.exists()
    assert recent_snapshot.exists()
    assert manifest["retention_removed"][0]["path"] == str(old_snapshot)


def test_backup_copies_root_file_through_latest_tmp(tmp_path, monkeypatch):
    module = _load_backup_module()
    project = tmp_path / "project"
    dest = tmp_path / "drive"
    project.mkdir()
    dest.mkdir()
    (project / "config.yaml").write_text("project: pm25\n", encoding="utf-8")

    monkeypatch.setattr(module, "BACKUP_SOURCES", ("config.yaml",))

    exit_code, manifest, _ = module.run_backup(
        project_root=project,
        dest_root=dest,
        no_snapshot=True,
        now=datetime(2026, 7, 1, 8, 30, tzinfo=timezone.utc),
    )

    latest_tmp = dest / "latest_tmp_20260701_083000"
    assert exit_code == 0
    assert manifest["status"] == "ok"
    assert manifest["latest_updated"] is True
    assert manifest["latest_tmp_dir"] == str(latest_tmp)
    assert manifest["files"][0]["destination"] == str(latest_tmp / "config.yaml")
    assert (dest / "latest" / "config.yaml").read_text(encoding="utf-8") == "project: pm25\n"
    assert not latest_tmp.exists()


def test_backup_creates_parent_directories_for_nested_files(tmp_path, monkeypatch):
    module = _load_backup_module()
    project = tmp_path / "project"
    dest = tmp_path / "drive"
    nested_file = project / "data" / "processed" / "daily" / "pm25.csv"
    nested_file.parent.mkdir(parents=True)
    dest.mkdir()
    nested_file.write_text("timestamp,pm25\n", encoding="utf-8")

    monkeypatch.setattr(module, "BACKUP_SOURCES", ("data/processed",))

    exit_code, manifest, _ = module.run_backup(
        project_root=project,
        dest_root=dest,
        no_snapshot=True,
        now=datetime(2026, 7, 1, 8, 31, tzinfo=timezone.utc),
    )

    assert exit_code == 0
    assert manifest["status"] == "ok"
    assert (
        dest / "latest" / "data" / "processed" / "daily" / "pm25.csv"
    ).read_text(encoding="utf-8") == "timestamp,pm25\n"


def test_backup_failed_does_not_delete_existing_latest(tmp_path, monkeypatch):
    module = _load_backup_module()
    project = tmp_path / "project"
    dest = tmp_path / "drive"
    project.mkdir()
    (dest / "latest").mkdir(parents=True)
    (dest / "latest" / "config.yaml").write_text("old: true\n", encoding="utf-8")
    (project / "config.yaml").write_text("new: true\n", encoding="utf-8")

    monkeypatch.setattr(module, "BACKUP_SOURCES", ("config.yaml", "README.md"))

    exit_code, manifest, manifest_path = module.run_backup(
        project_root=project,
        dest_root=dest,
        no_snapshot=False,
        now=datetime(2026, 7, 1, 8, 32, tzinfo=timezone.utc),
    )

    latest_tmp = dest / "latest_tmp_20260701_083200"
    assert exit_code == 1
    assert manifest["status"] == "failed"
    assert manifest["latest_updated"] is False
    assert manifest["latest_tmp_retained"] is True
    assert manifest["files_missing"] == 1
    assert (dest / "latest" / "config.yaml").read_text(encoding="utf-8") == "old: true\n"
    assert (latest_tmp / "config.yaml").read_text(encoding="utf-8") == "new: true\n"
    assert not (dest / "latest_previous").exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "failed"


def test_successful_backup_replaces_latest(tmp_path, monkeypatch):
    module = _load_backup_module()
    project = tmp_path / "project"
    dest = tmp_path / "drive"
    project.mkdir()
    (dest / "latest").mkdir(parents=True)
    (dest / "latest" / "config.yaml").write_text("old: true\n", encoding="utf-8")
    (project / "config.yaml").write_text("new: true\n", encoding="utf-8")

    monkeypatch.setattr(module, "BACKUP_SOURCES", ("config.yaml",))

    exit_code, manifest, _ = module.run_backup(
        project_root=project,
        dest_root=dest,
        no_snapshot=True,
        now=datetime(2026, 7, 1, 8, 33, tzinfo=timezone.utc),
    )

    assert exit_code == 0
    assert manifest["status"] == "ok"
    assert manifest["latest_updated"] is True
    assert (dest / "latest" / "config.yaml").read_text(encoding="utf-8") == "new: true\n"
    assert not (dest / "latest_previous").exists()


def test_destination_wait_retries_then_fails_clearly(tmp_path):
    module = _load_backup_module()
    sleep_calls: list[int] = []

    with pytest.raises(module.BackupError) as excinfo:
        module.ensure_destination(
            tmp_path / "missing_drive",
            attempts=3,
            wait_seconds=30,
            sleep_fn=sleep_calls.append,
        )

    assert sleep_calls == [30, 30]
    assert (
        "Backup destination is not available; Google Drive may not be running or mounted."
        in str(excinfo.value)
    )


def test_stale_temp_cleanup_requires_matching_failed_retained_manifest(tmp_path):
    module = _load_backup_module()
    dest = tmp_path / "drive"
    manifests = dest / "manifests"
    eligible = dest / "latest_tmp_20260701_010000"
    unproven = dest / "latest_tmp_20260701_020000"
    manifests.mkdir(parents=True)
    eligible.mkdir()
    unproven.mkdir()
    (manifests / "manifest_20260701_010000.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "latest_tmp_retained": True,
                "latest_tmp_dir": str(eligible),
            }
        ),
        encoding="utf-8",
    )
    old = datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()
    os.utime(eligible, (old, old))
    os.utime(unproven, (old, old))

    records = module.cleanup_stale_temp_dirs(
        dest,
        dry_run=True,
        now=datetime(2026, 7, 30, tzinfo=timezone.utc),
        stale_days=7,
    )

    by_name = {Path(record["path"]).name: record for record in records}
    assert by_name[eligible.name]["eligible"] is True
    assert by_name[unproven.name]["eligible"] is False
    assert "no matching manifest" in by_name[unproven.name]["reason"]
    assert eligible.exists()


def test_stale_temp_cleanup_removes_only_proven_directory(tmp_path):
    module = _load_backup_module()
    dest = tmp_path / "drive"
    manifests = dest / "manifests"
    staging = dest / "latest_tmp_20260701_010000"
    manifests.mkdir(parents=True)
    staging.mkdir()
    (manifests / "manifest_20260701_010000.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "latest_tmp_retained": True,
                "latest_tmp_dir": str(staging),
            }
        ),
        encoding="utf-8",
    )
    old = datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()
    os.utime(staging, (old, old))

    records = module.cleanup_stale_temp_dirs(
        dest,
        dry_run=False,
        now=datetime(2026, 7, 30, tzinfo=timezone.utc),
        stale_days=7,
    )

    assert records[0]["removed"] is True
    assert not staging.exists()
