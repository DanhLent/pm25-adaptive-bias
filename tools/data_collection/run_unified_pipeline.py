from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pm25_alert.alert.latest_snapshot import make_latest_snapshot
from pm25_alert.data.loading import load_config
from pm25_alert.data.preparation import prepare_canonical_data
from pm25_alert.evaluation import evaluate_alpha_candidates
from pm25_alert.hardware import process_hardware_timeline
from pm25_alert.state import (
    ExclusivePipelineLock,
    PipelineLockedError,
    read_pipeline_state,
    write_json_atomic,
)
from tools.data_collection.purpleair_collector import run_collector


STATUS_PATH = ROOT / "data/live/status/latest_unified_pipeline_run.json"
STATUS_REPORT = ROOT / "reports/PM25_UNIFIED_PIPELINE_STATUS.md"
LOG_DIR = ROOT / "logs/unified_pipeline"
T = TypeVar("T")


class PipelineStepError(RuntimeError):
    """An operational failure tied to one named orchestration step."""

    def __init__(self, step_name: str, message: str) -> None:
        super().__init__(message)
        self.step_name = step_name


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = pd.Timestamp(value)
    if parsed.tzinfo is None:
        parsed = parsed.tz_localize("UTC")
    return parsed.tz_convert("UTC").to_pydatetime()


def is_due(last_success: str | None, now: datetime, interval: timedelta) -> bool:
    previous = parse_utc(last_success)
    return previous is None or now - previous >= interval


def backup_decision(
    state: dict[str, Any],
    now: datetime,
    interval: timedelta,
    *,
    skip_backup: bool,
) -> dict[str, Any]:
    """Return a persisted-state backup decision with an operator-readable reason."""
    last_reconciliation = parse_utc(state.get("last_reconciliation"))
    last_backup = parse_utc(state.get("last_backup"))
    interval_due = is_due(state.get("last_backup"), now, interval)
    reconciliation_newer = last_reconciliation is not None and (
        last_backup is None or last_reconciliation > last_backup
    )
    successful_reconciliation_available = last_reconciliation is not None
    needed = interval_due or reconciliation_newer
    eligible = (
        needed
        and successful_reconciliation_available
        and not skip_backup
    )
    if skip_backup:
        reason = "--skip-backup"
    elif not successful_reconciliation_available:
        reason = "no_successful_reconciliation"
    elif reconciliation_newer:
        reason = "reconciliation_newer_than_last_backup"
    elif interval_due:
        reason = "backup_interval_due"
    else:
        reason = "not_due"
    return {
        "needed": needed,
        "eligible": eligible,
        "reason": reason,
        "interval_due": interval_due,
        "reconciliation_newer_than_backup": reconciliation_newer,
        "successful_reconciliation_available": successful_reconciliation_available,
    }


def _sanitize_text(value: object) -> str:
    text = str(value)
    sensitive_value = os.environ.get("PURPLEAIR_API_KEY")
    if sensitive_value:
        text = text.replace(sensitive_value, "[REDACTED]")
    patterns = (
        r"(?i)\b(authorization)\s*[:=]\s*([^\s,;]+(?:\s+[^\s,;]+)?)",
        r"(?i)\b(x-api-key|api[_ -]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)",
        r"(?i)\b(bearer)\s+([^\s,;]+)",
    )
    for pattern in patterns:
        text = re.sub(pattern, lambda match: f"{match.group(1)}: [REDACTED]", text)
    return text


def _sanitize_for_output(value: Any, key: str | None = None) -> Any:
    sensitive_key = bool(
        key
        and re.search(
            r"(?i)(authorization|api[_-]?key|token|password|secret)",
            key,
        )
        and not key.lower().endswith(("_set", "_present"))
    )
    if sensitive_key and value not in (None, False, True):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(item_key): _sanitize_for_output(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_for_output(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_for_output(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _append_failed_step(
    status: dict[str, Any],
    step_name: str,
    exc: Exception,
) -> PipelineStepError:
    message = _sanitize_text(f"{type(exc).__name__}: {exc}")
    status["steps"].append(
        {"name": step_name, "status": "failed", "error": message}
    )
    return PipelineStepError(step_name, message)


def _run_status_step(
    status: dict[str, Any],
    step_name: str,
    operation: Callable[[], T],
) -> T:
    try:
        summary = operation()
    except Exception as exc:
        raise _append_failed_step(status, step_name, exc) from exc
    status["steps"].append(
        {"name": step_name, "status": "ok", "summary": summary}
    )
    return summary


def _run_command(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    record = {
        "command": command,
        "return_code": result.returncode,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with return code {result.returncode}: {' '.join(command)}\n"
            f"{result.stderr[-1000:]}"
        )
    return record


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        suffix=".tmp",
        prefix=f"{path.name}.",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(text)
            handle.flush()
        temporary.replace(path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def _write_status(status: dict[str, Any]) -> None:
    public_status = _sanitize_for_output(status)
    write_json_atomic(STATUS_PATH, public_status)
    due = public_status.get("due") or {}
    lines = [
        "# PM2.5 Unified Pipeline Status",
        "",
        f"- Status: `{public_status.get('status', 'unknown')}`",
        f"- Started UTC: {public_status.get('started_at_utc')}",
        f"- Ended UTC: {public_status.get('ended_at_utc')}",
        f"- Offline: {public_status.get('offline')}",
        f"- Reconciliation due: {due.get('reconciliation', 'unknown')}",
        f"- Backup due: {due.get('backup', 'unknown')}",
        f"- Backup reason: {due.get('backup_reason', 'unknown')}",
        f"- Alpha evaluation due: {due.get('alpha_evaluation', 'unknown')}",
        "",
        "## Steps",
        "",
        "| Step | Status |",
        "| --- | --- |",
    ]
    for step in public_status.get("steps", []):
        lines.append(f"| {step['name']} | {step['status']} |")
    if public_status.get("error"):
        error = str(public_status["error"]).replace("|", "\\|").replace("\n", " ")
        lines.extend(["", "## Error", "", f"`{error}`"])
    _write_text_atomic(STATUS_REPORT, "\n".join(lines) + "\n")


def _append_daily_log(status: dict[str, Any], now: datetime) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"unified_pipeline_{now.strftime('%Y%m%d')}.log"
    public_status = _sanitize_for_output(status)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(public_status, sort_keys=True, default=str) + "\n")
    return log_path


def _dry_run_summary(config: dict[str, Any], now: datetime, args: argparse.Namespace) -> dict[str, Any]:
    hardware = config["hardware_aligned"]
    state = read_pipeline_state(ROOT / hardware["state_json"]) or {}
    operations = config["operations"]
    backup = backup_decision(
        state,
        now,
        timedelta(hours=float(operations["backup_interval_hours"])),
        skip_backup=args.skip_backup,
    )
    due = {
        "reconciliation": args.force_reconciliation
        or is_due(
            state.get("last_reconciliation"),
            now,
            timedelta(hours=float(operations["reconciliation_interval_hours"])),
        ),
        "backup": backup["needed"],
        "backup_eligible_now": backup["eligible"],
        "backup_reason": backup["reason"],
        "alpha_evaluation": is_due(
            state.get("last_alpha_evaluation"),
            now,
            timedelta(days=float(operations["alpha_evaluation_interval_days"])),
        ),
    }
    return {
        "status": "dry_run",
        "now_utc": now.isoformat(),
        "offline": args.offline,
        "due": due,
        "planned_steps": [
            "incremental/reconciliation collection" if not args.offline else "collection skipped (--offline)",
            "canonical append/dedup + two-level QC + CAMS left timeline",
            "hardware-aligned incremental/replay processing",
            "atomic latest snapshot",
            "daily backup after successful reconciliation" if not args.skip_backup else "backup skipped",
            "weekly alpha candidate evaluation" if not args.skip_alpha_evaluation else "alpha evaluation skipped",
        ],
    }


def _build_status(
    config: dict[str, Any],
    now: datetime,
    args: argparse.Namespace,
) -> dict[str, Any]:
    hardware = config["hardware_aligned"]
    operations = config["operations"]
    state = read_pipeline_state(ROOT / hardware["state_json"]) or {}
    reconciliation_due = args.force_reconciliation or is_due(
        state.get("last_reconciliation"),
        now,
        timedelta(hours=float(operations["reconciliation_interval_hours"])),
    )
    backup = backup_decision(
        state,
        now,
        timedelta(hours=float(operations["backup_interval_hours"])),
        skip_backup=args.skip_backup,
    )
    alpha_due = is_due(
        state.get("last_alpha_evaluation"),
        now,
        timedelta(days=float(operations["alpha_evaluation_interval_days"])),
    )
    return {
        "status": "running",
        "started_at_utc": now.isoformat(),
        "ended_at_utc": None,
        "offline": args.offline,
        "due": {
            "reconciliation": reconciliation_due,
            "backup": backup["needed"],
            "backup_eligible_now": backup["eligible"],
            "backup_reason": backup["reason"],
            "alpha_evaluation": alpha_due,
        },
        "steps": [],
        "error": None,
    }


def execute_pipeline(
    *,
    config: dict[str, Any],
    now: datetime,
    args: argparse.Namespace,
    status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hardware = config["hardware_aligned"]
    operations = config["operations"]
    state_path = ROOT / hardware["state_json"]
    status = status if status is not None else _build_status(config, now, args)
    reconciliation_due = bool(status["due"]["reconciliation"])
    alpha_due = bool(status["due"]["alpha_evaluation"])

    raw_success_timestamp = None
    reconciliation_completed = False
    if args.offline:
        status["steps"].append(
            {"name": "collection", "status": "skipped_offline"}
        )
    else:
        purpleair = _run_status_step(
            status,
            "purpleair_collection",
            lambda: run_collector(
                args.config,
                reconcile=reconciliation_due,
                now=now,
            ),
        )
        raw_success_timestamp = purpleair.get("last_successful_raw_timestamp")
        cams_command = [
            sys.executable,
            "tools/data_collection/07_fetch_openmeteo_cams.py",
        ]
        if reconciliation_due:
            cams_command.append("--reconcile")
        _run_status_step(
            status,
            "cams_collection",
            lambda: _run_command(cams_command),
        )
        reconciliation_completed = reconciliation_due

    _run_status_step(
        status,
        "canonical_prepare_qc",
        lambda: prepare_canonical_data(ROOT, config),
    )
    input_path = ROOT / hardware["hourly_input_csv"]
    _run_status_step(
        status,
        "hardware_aligned",
        lambda: process_hardware_timeline(
            pd.read_csv(input_path),
            config=config,
            trace_path=ROOT / hardware["trace_csv"],
            state_path=state_path,
        ),
    )
    _run_status_step(
        status,
        "latest_snapshot",
        lambda: make_latest_snapshot(
            ROOT / hardware["trace_csv"],
            ROOT / hardware["latest_output_dir"],
        ),
    )

    state = read_pipeline_state(state_path)
    if state is None:
        raise _append_failed_step(
            status,
            "state_persistence",
            RuntimeError("Hardware processing did not create pipeline state."),
        )
    if raw_success_timestamp:
        state["last_successful_raw_timestamp"] = raw_success_timestamp
    if reconciliation_completed:
        state["last_reconciliation"] = now.isoformat()
    write_json_atomic(state_path, state)

    backup = backup_decision(
        state,
        now,
        timedelta(hours=float(operations["backup_interval_hours"])),
        skip_backup=args.skip_backup,
    )
    status["due"]["backup"] = backup["needed"]
    status["due"]["backup_eligible_now"] = backup["eligible"]
    status["due"]["backup_reason"] = backup["reason"]
    if args.skip_backup:
        status["steps"].append(
            {
                "name": "daily_backup",
                "status": "skipped",
                "reason": "--skip-backup",
            }
        )
    elif backup["eligible"]:
        destination = str(operations["backup_destination"])

        def perform_backup() -> dict[str, Any]:
            backup_summary = _run_command(
                [
                    sys.executable,
                    "tools/backup/backup_pm25_data.py",
                    "--dest",
                    destination,
                ]
            )
            updated_state = read_pipeline_state(state_path) or state
            updated_state["last_backup"] = now.isoformat()
            write_json_atomic(state_path, updated_state)
            return backup_summary

        _run_status_step(status, "daily_backup", perform_backup)
    elif backup["needed"]:
        status["steps"].append(
            {
                "name": "daily_backup",
                "status": "skipped",
                "reason": backup["reason"],
            }
        )
    else:
        status["steps"].append(
            {"name": "daily_backup", "status": "not_due", "reason": "not_due"}
        )

    if alpha_due and not args.skip_alpha_evaluation:
        def perform_alpha_evaluation() -> dict[str, Any]:
            report = evaluate_alpha_candidates(
                pd.read_csv(input_path),
                config=config,
                output_dir=ROOT / "reports/alpha_evaluation",
            )
            updated_state = read_pipeline_state(state_path) or state
            updated_state["last_alpha_evaluation"] = now.isoformat()
            write_json_atomic(state_path, updated_state)
            return report

        report = _run_status_step(
            status,
            "weekly_alpha_evaluation",
            perform_alpha_evaluation,
        )
        status["steps"][-1]["status"] = str(report.get("status", "ok"))
    elif alpha_due:
        status["steps"].append(
            {
                "name": "weekly_alpha_evaluation",
                "status": "skipped",
                "reason": "--skip-alpha-evaluation",
            }
        )
    else:
        status["steps"].append(
            {
                "name": "weekly_alpha_evaluation",
                "status": "not_due",
                "reason": "not_due",
            }
        )

    status["status"] = "ok"
    status["ended_at_utc"] = utc_now().isoformat()
    return status


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the single hourly PM2.5 collection/QC/hardware pipeline."
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use local/reference data without making API calls.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-reconciliation", action="store_true")
    parser.add_argument("--skip-backup", action="store_true")
    parser.add_argument("--skip-alpha-evaluation", action="store_true")
    parser.add_argument(
        "--now",
        help="Deterministic UTC timestamp for tests, for example 2026-07-30T16:00:00Z.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    args.config = str(config_path.resolve())
    config = load_config(config_path)
    now = parse_utc(args.now) if args.now else utc_now()
    assert now is not None
    if args.dry_run:
        summary = _dry_run_summary(config, now, args)
        if not args.offline:
            run_collector(config_path, dry_run=True, reconcile=summary["due"]["reconciliation"], now=now)
        print(json.dumps(summary, indent=2))
        return 0

    lock_path = ROOT / config["hardware_aligned"]["lock_file"]
    status = _build_status(config, now, args)
    exit_code = 0
    try:
        with ExclusivePipelineLock(lock_path):
            try:
                status = execute_pipeline(
                    config=config,
                    now=now,
                    args=args,
                    status=status,
                )
            except Exception as exc:
                if not status["steps"] or status["steps"][-1].get("status") != "failed":
                    _append_failed_step(status, "orchestration", exc)
                status["status"] = "failed"
                status["ended_at_utc"] = utc_now().isoformat()
                status["error"] = _sanitize_text(exc)
                exit_code = 1
            _write_status(status)
            _append_daily_log(status, now)
    except PipelineLockedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    public_status = _sanitize_for_output(status)
    output = json.dumps(public_status, indent=2, default=str)
    print(output, file=sys.stderr if exit_code else sys.stdout)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
