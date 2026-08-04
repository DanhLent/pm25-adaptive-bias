from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEST = Path(r"G:\My Drive\PM25_Backup")
CHECKSUM_MAX_BYTES = 256 * 1024 * 1024
DESTINATION_UNAVAILABLE_MESSAGE = (
    "Backup destination is not available; Google Drive may not be running or mounted."
)
DESTINATION_WAIT_ATTEMPTS = 10
DESTINATION_WAIT_SECONDS = 30

BACKUP_SOURCES = (
    "data/live/purpleair/purpleair_10min.csv",
    "data/live/purpleair/purpleair_live_hourly.csv",
    "data/live/purpleair/latest_run.json",
    "data/live/state/pm25_pipeline_state.json",
    "data/live/status/latest_unified_pipeline_run.json",
    "data/live/status/latest_pipeline_run.json",
    "data/interim",
    "data/processed",
    "outputs/predictions",
    "outputs/metrics",
    "outputs/latest",
    "reports/alpha_evaluation",
    "reports/PM25_DATA_MIGRATION_QC_REPORT.md",
    "reports/STAGE_3_STATUS.md",
    "reports/STAGE_2_EVALUATION.md",
    "config.yaml",
    "README.md",
)

FORBIDDEN_PARTS = {".venv", "__pycache__", ".pytest_cache"}
FORBIDDEN_PATHS = {
    "scripts/windows/run_pm25_hourly_update.bat",
    "scripts/windows/run_pm25_hourly_update.ps1",
}
FORBIDDEN_PREFIXES = {
    "data/live/purpleair/raw",
}
TEMP_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".temp",
    ".swp",
}


class BackupError(Exception):
    """Raised for user-facing backup failures."""


@dataclass(frozen=True)
class BackupCandidate:
    source: Path
    relative_path: Path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Back up PM2.5 project data to a local Google Drive folder.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help=f"Backup destination root. Default: {DEFAULT_DEST}",
    )
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Copy latest/ and write a manifest without creating a zip snapshot.",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=30,
        help="Delete snapshots older than this many days. Default: 30.",
    )
    parser.add_argument(
        "--audit-stale-temp",
        action="store_true",
        help="Only report stale latest_tmp_* directories; do not run a backup.",
    )
    parser.add_argument(
        "--cleanup-stale-temp",
        action="store_true",
        help="Remove only stale latest_tmp_* directories proven failed by a matching manifest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --cleanup-stale-temp, report eligible removals without deleting.",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=7,
        help="Minimum retained staging age for stale audit/cleanup. Default: 7.",
    )
    return parser


def normalize_relative_path(path: Path | str) -> str:
    return Path(path).as_posix()


def is_relative_to_path(path: Path, prefix: Path) -> bool:
    try:
        path.relative_to(prefix)
        return True
    except ValueError:
        return False


def is_forbidden(relative_path: Path) -> tuple[bool, str | None]:
    rel_posix = normalize_relative_path(relative_path)
    parts = set(relative_path.parts)
    if parts & FORBIDDEN_PARTS:
        return True, "forbidden cache/environment path"
    if rel_posix in FORBIDDEN_PATHS:
        return True, "forbidden runner may contain API keys"
    for prefix in FORBIDDEN_PREFIXES:
        if rel_posix == prefix or rel_posix.startswith(f"{prefix}/"):
            return True, "forbidden heavy/raw data path"
    if relative_path.suffix.lower() in TEMP_SUFFIXES:
        return True, "temporary or bytecode file"
    return False, None


def iter_backup_candidates(
    project_root: Path,
    sources: Iterable[str] | None = None,
) -> tuple[list[BackupCandidate], list[dict[str, object]], list[dict[str, object]]]:
    candidates: list[BackupCandidate] = []
    skipped: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    if sources is None:
        sources = BACKUP_SOURCES

    for source_name in sources:
        relative_source = Path(source_name)
        forbidden, reason = is_forbidden(relative_source)
        if forbidden:
            skipped.append(
                {
                    "path": normalize_relative_path(relative_source),
                    "reason": reason,
                }
            )
            continue

        absolute_source = project_root / relative_source
        if not absolute_source.exists():
            errors.append(
                {
                    "path": normalize_relative_path(relative_source),
                    "error": "source path does not exist",
                }
            )
            continue

        if absolute_source.is_file():
            candidates.append(BackupCandidate(absolute_source, relative_source))
            continue

        if absolute_source.is_dir():
            for child in sorted(absolute_source.rglob("*")):
                if not child.is_file():
                    continue
                relative_child = child.relative_to(project_root)
                forbidden, reason = is_forbidden(relative_child)
                if forbidden:
                    skipped.append(
                        {
                            "path": normalize_relative_path(relative_child),
                            "reason": reason,
                        }
                    )
                    continue
                candidates.append(BackupCandidate(child, relative_child))
            continue

        skipped.append(
            {
                "path": normalize_relative_path(relative_source),
                "reason": "not a regular file or directory",
            }
        )

    return candidates, skipped, errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_destination_child(
    path: Path,
    dest_root: Path,
    *,
    expected_name: str | None = None,
    expected_prefix: str | None = None,
) -> None:
    resolved_dest = dest_root.resolve()
    resolved_parent = path.parent.resolve()
    if resolved_parent != resolved_dest:
        raise BackupError(f"Refusing to operate on path outside destination root: {path}")
    if expected_name is not None and path.name != expected_name:
        raise BackupError(f"Refusing to operate on unexpected path: {path}")
    if expected_prefix is not None and not path.name.startswith(expected_prefix):
        raise BackupError(f"Refusing to operate on unexpected staging path: {path}")


def remove_destination_dir(path: Path, dest_root: Path, *, expected_name: str) -> None:
    validate_destination_child(path, dest_root, expected_name=expected_name)
    if not path.exists():
        return
    if not path.is_dir() or path.is_symlink():
        raise BackupError(f"Refusing to remove non-directory backup path: {path}")
    shutil.rmtree(path)


def replace_latest_atomically(
    *,
    latest_tmp_dir: Path,
    latest_dir: Path,
    latest_previous_dir: Path,
    dest_root: Path,
) -> list[dict[str, object]]:
    validate_destination_child(latest_tmp_dir, dest_root, expected_prefix="latest_tmp_")
    validate_destination_child(latest_dir, dest_root, expected_name="latest")
    validate_destination_child(latest_previous_dir, dest_root, expected_name="latest_previous")

    if not latest_tmp_dir.is_dir():
        raise BackupError(f"Staging directory is missing: {latest_tmp_dir}")
    if latest_dir.exists() and (not latest_dir.is_dir() or latest_dir.is_symlink()):
        raise BackupError(f"Refusing to replace non-directory latest path: {latest_dir}")

    remove_destination_dir(latest_previous_dir, dest_root, expected_name="latest_previous")

    moved_latest = False
    if latest_dir.exists():
        try:
            latest_dir.rename(latest_previous_dir)
            moved_latest = True
        except Exception as exc:
            raise BackupError(f"Failed to move existing latest to latest_previous: {exc}") from exc

    try:
        latest_tmp_dir.rename(latest_dir)
    except Exception as exc:
        rollback_error = None
        if moved_latest and latest_previous_dir.exists() and not latest_dir.exists():
            try:
                latest_previous_dir.rename(latest_dir)
            except Exception as rollback_exc:  # pragma: no cover - rare filesystem guard
                rollback_error = rollback_exc
        if rollback_error is not None:
            raise BackupError(
                "Failed to promote latest_tmp to latest, and rollback also failed: "
                f"{exc}; rollback error: {rollback_error}"
            ) from exc
        raise BackupError(f"Failed to promote latest_tmp to latest: {exc}") from exc

    warnings: list[dict[str, object]] = []
    if moved_latest and latest_previous_dir.exists():
        try:
            shutil.rmtree(latest_previous_dir)
        except Exception as exc:  # pragma: no cover - defensive filesystem guard
            warnings.append(
                {
                    "path": str(latest_previous_dir),
                    "warning": f"latest was updated, but latest_previous cleanup failed: {exc}",
                }
            )
    return warnings


def zip_directory(source_dir: Path, zip_path: Path) -> int:
    file_count = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            archive.write(path, path.relative_to(source_dir).as_posix())
            file_count += 1
    return file_count


def apply_snapshot_retention(
    snapshots_dir: Path,
    keep_days: int,
    now: datetime,
) -> list[dict[str, object]]:
    if keep_days < 0:
        raise BackupError("--keep-days must be 0 or greater")

    cutoff = now - timedelta(days=keep_days)
    removed: list[dict[str, object]] = []
    for snapshot in sorted(snapshots_dir.glob("pm25_backup_*.zip")):
        modified = datetime.fromtimestamp(snapshot.stat().st_mtime, tz=now.tzinfo)
        if modified >= cutoff:
            continue
        size_bytes = snapshot.stat().st_size
        snapshot.unlink()
        removed.append(
            {
                "path": str(snapshot),
                "modified_at": modified.isoformat(),
                "size_bytes": size_bytes,
            }
        )
    return removed


def ensure_destination(
    dest_root: Path,
    *,
    attempts: int = DESTINATION_WAIT_ATTEMPTS,
    wait_seconds: int = DESTINATION_WAIT_SECONDS,
    sleep_fn=time.sleep,
) -> None:
    if attempts < 1:
        raise BackupError("Destination wait attempts must be at least 1")

    for attempt in range(1, attempts + 1):
        if dest_root.exists():
            if not dest_root.is_dir():
                raise BackupError(f"Backup destination is not a directory: {dest_root}")
            return

        if attempt < attempts:
            print(
                f"{DESTINATION_UNAVAILABLE_MESSAGE} "
                f"Waiting {wait_seconds} seconds before retry "
                f"{attempt + 1}/{attempts}: {dest_root}",
                file=sys.stderr,
            )
            sleep_fn(wait_seconds)

    raise BackupError(f"{DESTINATION_UNAVAILABLE_MESSAGE} Path: {dest_root}")


def audit_stale_temp_dirs(
    dest_root: Path,
    *,
    now: datetime | None = None,
    stale_days: int = 7,
) -> list[dict[str, object]]:
    """Classify staging dirs; only failed, retained, old, manifest-backed dirs qualify."""
    if stale_days < 0:
        raise BackupError("--stale-days must be 0 or greater")
    dest_root = dest_root.resolve()
    ensure_destination(dest_root, attempts=1, wait_seconds=0)
    manifests_dir = dest_root / "manifests"
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = current - timedelta(days=stale_days)

    manifests_by_tmp: dict[str, dict[str, object]] = {}
    if manifests_dir.is_dir():
        for manifest_path in sorted(manifests_dir.glob("manifest_*.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                tmp_value = manifest.get("latest_tmp_dir")
                if tmp_value:
                    manifests_by_tmp[str(Path(tmp_value).resolve())] = {
                        "manifest": manifest,
                        "manifest_path": str(manifest_path),
                    }
            except Exception:
                continue

    records: list[dict[str, object]] = []
    for staging in sorted(dest_root.glob("latest_tmp_*")):
        validate_destination_child(staging, dest_root, expected_prefix="latest_tmp_")
        modified = datetime.fromtimestamp(staging.stat().st_mtime, tz=timezone.utc)
        match = manifests_by_tmp.get(str(staging.resolve()))
        reason = None
        eligible = False
        manifest_path = None
        if not staging.is_dir() or staging.is_symlink():
            reason = "not a regular staging directory"
        elif match is None:
            reason = "no matching manifest"
        else:
            manifest = match["manifest"]
            assert isinstance(manifest, dict)
            manifest_path = match["manifest_path"]
            if manifest.get("status") != "failed":
                reason = "matching manifest is not failed"
            elif manifest.get("latest_tmp_retained") is not True:
                reason = "matching manifest does not prove retained staging"
            elif modified > cutoff:
                reason = f"younger than {stale_days} days"
            else:
                eligible = True
                reason = "eligible: failed retained staging with matching stale manifest"
        records.append(
            {
                "path": str(staging),
                "modified_at_utc": modified.isoformat(),
                "manifest_path": manifest_path,
                "eligible": eligible,
                "reason": reason,
            }
        )
    return records


def cleanup_stale_temp_dirs(
    dest_root: Path,
    *,
    dry_run: bool,
    now: datetime | None = None,
    stale_days: int = 7,
) -> list[dict[str, object]]:
    records = audit_stale_temp_dirs(
        dest_root,
        now=now,
        stale_days=stale_days,
    )
    for record in records:
        record["removed"] = False
        if not record["eligible"] or dry_run:
            continue
        staging = Path(str(record["path"]))
        validate_destination_child(staging, dest_root.resolve(), expected_prefix="latest_tmp_")
        if staging.is_dir() and not staging.is_symlink():
            shutil.rmtree(staging)
            record["removed"] = True
    return records


def make_manifest(
    *,
    project_root: Path,
    dest_root: Path,
    latest_dir: Path,
    latest_tmp_dir: Path,
    latest_previous_dir: Path,
    timestamp: str,
    started_at: datetime,
    keep_days: int,
    no_snapshot: bool,
) -> dict[str, object]:
    return {
        "status": "ok",
        "backup_started_at": started_at.isoformat(),
        "backup_timestamp": timestamp,
        "project_root": str(project_root),
        "destination_root": str(dest_root),
        "latest_dir": str(latest_dir),
        "latest_tmp_dir": str(latest_tmp_dir),
        "latest_previous_dir": str(latest_previous_dir),
        "latest_updated": False,
        "latest_tmp_retained": False,
        "snapshot_path": None,
        "snapshot_created": False,
        "snapshot_source_dir": None,
        "snapshot_file_count": 0,
        "no_snapshot": no_snapshot,
        "keep_days": keep_days,
        "files_copied": 0,
        "files_failed": 0,
        "files_missing": 0,
        "files": [],
        "missing_files": [],
        "skipped": [],
        "errors": [],
        "warnings": [],
        "retention_removed": [],
        "summary": {
            "files_copied": 0,
            "bytes_copied": 0,
            "files_failed": 0,
            "files_missing": 0,
        },
    }


def sync_manifest_summary(manifest: dict[str, object]) -> None:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    manifest["files_copied"] = int(summary["files_copied"])
    manifest["files_failed"] = int(summary["files_failed"])
    manifest["files_missing"] = int(summary["files_missing"])


def record_error(
    manifest: dict[str, object],
    *,
    path: str,
    error: str,
) -> None:
    errors = manifest["errors"]
    assert isinstance(errors, list)
    errors.append({"path": path, "error": error})
    manifest["status"] = "failed"


def copy_candidates_to_dir(
    *,
    candidates: Iterable[BackupCandidate],
    destination_root: Path,
    manifest: dict[str, object],
) -> None:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    files_manifest = manifest["files"]
    assert isinstance(files_manifest, list)

    for candidate in candidates:
        relative_path = candidate.relative_path
        destination_path = destination_root / relative_path
        record: dict[str, object] = {
            "source": normalize_relative_path(relative_path),
            "destination": str(destination_path),
            "size_bytes": None,
            "checksum_sha256": None,
            "checksum_note": None,
            "status": "ok",
            "error": None,
        }

        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate.source, destination_path)
            size_bytes = destination_path.stat().st_size
            record["size_bytes"] = size_bytes
            if size_bytes <= CHECKSUM_MAX_BYTES:
                record["checksum_sha256"] = sha256_file(destination_path)
            else:
                record["checksum_note"] = (
                    f"skipped because file is larger than {CHECKSUM_MAX_BYTES} bytes"
                )
            summary["files_copied"] = int(summary["files_copied"]) + 1
            summary["bytes_copied"] = int(summary["bytes_copied"]) + size_bytes
        except Exception as exc:  # pragma: no cover - defensive filesystem guard
            record["status"] = "failed"
            record["error"] = str(exc)
            summary["files_failed"] = int(summary["files_failed"]) + 1
            record_error(
                manifest,
                path=normalize_relative_path(relative_path),
                error=str(exc),
            )

        files_manifest.append(record)


def run_backup(
    *,
    project_root: Path = PROJECT_ROOT,
    dest_root: Path = DEFAULT_DEST,
    no_snapshot: bool = False,
    keep_days: int = 30,
    now: datetime | None = None,
) -> tuple[int, dict[str, object], Path]:
    project_root = project_root.resolve()
    dest_root = dest_root.resolve()
    ensure_destination(dest_root)

    started_at = now or datetime.now(timezone.utc).astimezone()
    timestamp = started_at.strftime("%Y%m%d_%H%M%S")

    latest_dir = dest_root / "latest"
    latest_tmp_dir = dest_root / f"latest_tmp_{timestamp}"
    latest_previous_dir = dest_root / "latest_previous"
    snapshots_dir = dest_root / "snapshots"
    manifests_dir = dest_root / "manifests"
    logs_dir = dest_root / "logs"

    snapshots_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    manifest = make_manifest(
        project_root=project_root,
        dest_root=dest_root,
        latest_dir=latest_dir,
        latest_tmp_dir=latest_tmp_dir,
        latest_previous_dir=latest_previous_dir,
        timestamp=timestamp,
        started_at=started_at,
        keep_days=keep_days,
        no_snapshot=no_snapshot,
    )

    summary = manifest["summary"]
    assert isinstance(summary, dict)
    errors_manifest = manifest["errors"]
    assert isinstance(errors_manifest, list)
    warnings_manifest = manifest["warnings"]
    assert isinstance(warnings_manifest, list)
    snapshot_attempted = False

    try:
        validate_destination_child(latest_tmp_dir, dest_root, expected_prefix="latest_tmp_")
        if latest_tmp_dir.exists():
            raise BackupError(f"Staging directory already exists: {latest_tmp_dir}")
        latest_tmp_dir.mkdir(parents=True, exist_ok=False)

        candidates, skipped, collection_errors = iter_backup_candidates(project_root)
        manifest["skipped"] = skipped
        manifest["missing_files"] = collection_errors
        summary["files_missing"] = len(collection_errors)
        errors_manifest.extend(collection_errors)

        copy_candidates_to_dir(
            candidates=candidates,
            destination_root=latest_tmp_dir,
            manifest=manifest,
        )
        sync_manifest_summary(manifest)

        if collection_errors or int(summary["files_failed"]) > 0:
            manifest["status"] = "failed"

        if manifest["status"] == "ok" and not no_snapshot:
            snapshot_path = snapshots_dir / f"pm25_backup_{timestamp}.zip"
            snapshot_attempted = True
            try:
                manifest["snapshot_source_dir"] = str(latest_tmp_dir)
                manifest["snapshot_file_count"] = zip_directory(latest_tmp_dir, snapshot_path)
                manifest["snapshot_created"] = True
                manifest["snapshot_path"] = str(snapshot_path)
            except Exception as exc:  # pragma: no cover - defensive filesystem guard
                manifest["status"] = "failed"
                errors_manifest.append(
                    {
                        "path": str(snapshot_path),
                        "error": f"snapshot creation failed: {exc}",
                    }
                )
                if snapshot_path.exists():
                    try:
                        snapshot_path.unlink()
                    except Exception as cleanup_exc:  # pragma: no cover
                        warnings_manifest.append(
                            {
                                "path": str(snapshot_path),
                                "warning": (
                                    "partial snapshot cleanup failed: "
                                    f"{cleanup_exc}"
                                ),
                            }
                        )

        if manifest["status"] == "ok":
            try:
                warnings_manifest.extend(
                    replace_latest_atomically(
                        latest_tmp_dir=latest_tmp_dir,
                        latest_dir=latest_dir,
                        latest_previous_dir=latest_previous_dir,
                        dest_root=dest_root,
                    )
                )
                manifest["latest_updated"] = True
            except BackupError as exc:
                record_error(manifest, path=str(latest_dir), error=str(exc))
        elif not no_snapshot and not snapshot_attempted:
            errors_manifest.append(
                {
                    "path": str(snapshots_dir),
                    "error": "snapshot skipped because backup status is failed",
                }
            )

    except Exception as exc:  # pragma: no cover - last-resort manifest guard
        record_error(manifest, path=str(latest_tmp_dir), error=str(exc))

    sync_manifest_summary(manifest)
    if not manifest["latest_updated"] and latest_tmp_dir.exists():
        manifest["latest_tmp_retained"] = True
        warnings_manifest.append(
            {
                "path": str(latest_tmp_dir),
                "warning": "latest_tmp retained for debugging; latest was not modified",
            }
        )

    if manifest["status"] == "ok":
        try:
            manifest["retention_removed"] = apply_snapshot_retention(
                snapshots_dir,
                keep_days,
                started_at,
            )
        except Exception as exc:  # pragma: no cover - retention is non-critical
            warnings_manifest.append(
                {
                    "path": str(snapshots_dir),
                    "warning": f"snapshot retention cleanup failed: {exc}",
                }
            )
    else:
        warnings_manifest.append(
            {
                "path": str(snapshots_dir),
                "warning": "snapshot retention skipped because backup status is failed",
            }
        )

    manifest_path = manifests_dir / f"manifest_{timestamp}.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return (0 if manifest["status"] == "ok" else 1), manifest, manifest_path


def print_summary(manifest: dict[str, object], manifest_path: Path) -> None:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    print(f"Backup status: {manifest['status']}")
    print(f"Files copied: {summary['files_copied']}")
    print(f"Bytes copied: {summary['bytes_copied']}")
    print(f"Latest folder: {manifest['latest_dir']}")
    print(f"Latest updated: {manifest['latest_updated']}")
    print(f"Latest tmp: {manifest['latest_tmp_dir']}")
    if manifest["latest_tmp_retained"]:
        print("Latest tmp retained: yes")
    if manifest["snapshot_created"]:
        print(f"Snapshot: {manifest['snapshot_path']}")
    elif manifest["no_snapshot"]:
        print("Snapshot: skipped (--no-snapshot)")
    else:
        print("Snapshot: not created")
    print(f"Manifest: {manifest_path}")

    errors = manifest["errors"]
    assert isinstance(errors, list)
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error.get('path')}: {error.get('error')}")

    warnings = manifest["warnings"]
    assert isinstance(warnings, list)
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning.get('path')}: {warning.get('warning')}")


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        if args.audit_stale_temp or args.cleanup_stale_temp:
            records = cleanup_stale_temp_dirs(
                args.dest,
                dry_run=args.dry_run or not args.cleanup_stale_temp,
                stale_days=args.stale_days,
            )
            print(json.dumps(records, indent=2))
            return 0
        exit_code, manifest, manifest_path = run_backup(
            dest_root=args.dest,
            no_snapshot=args.no_snapshot,
            keep_days=args.keep_days,
        )
    except BackupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - last-resort clarity
        print(f"ERROR: unexpected backup failure: {exc}", file=sys.stderr)
        return 2

    print_summary(manifest, manifest_path)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
