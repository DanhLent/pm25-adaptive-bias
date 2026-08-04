from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str):
    path = ROOT / "tools/data_collection/run_unified_pipeline.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _config() -> dict:
    return {
        "hardware_aligned": {
            "state_json": "data/live/state/pipeline.json",
            "hourly_input_csv": "data/processed/hourly.csv",
            "trace_csv": "outputs/predictions/trace.csv",
            "latest_output_dir": "outputs/latest",
            "lock_file": "data/live/state/pipeline.lock",
        },
        "operations": {
            "reconciliation_interval_hours": 24,
            "backup_interval_hours": 24,
            "alpha_evaluation_interval_days": 7,
            "backup_destination": "X:/fake-drive/PM25_Backup",
            "retry_backoff_seconds": [0],
        },
    }


def _install_paths(module, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(
        module,
        "STATUS_PATH",
        tmp_path / "data/live/status/latest_unified_pipeline_run.json",
    )
    monkeypatch.setattr(
        module,
        "STATUS_REPORT",
        tmp_path / "reports/PM25_UNIFIED_PIPELINE_STATUS.md",
    )
    monkeypatch.setattr(
        module,
        "LOG_DIR",
        tmp_path / "logs/unified_pipeline",
    )


def _install_success_fakes(
    module,
    tmp_path,
    monkeypatch,
    *,
    fail_step: str | None = None,
):
    config = _config()
    _install_paths(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "load_config", lambda path: config)
    monkeypatch.setattr(
        module.pd,
        "read_csv",
        lambda path: pd.DataFrame({"cams_pm25": [10.0]}),
    )
    secret_error = "injected failure Authorization: Bearer unit-secret"
    reconcile_flags: list[bool] = []
    command_calls: list[list[str]] = []

    def maybe_fail(step_name: str, value):
        if fail_step == step_name:
            raise RuntimeError(secret_error)
        return value

    def fake_collector(config_path, *, reconcile, now):
        reconcile_flags.append(reconcile)
        return maybe_fail(
            "purpleair_collection",
            {"last_successful_raw_timestamp": now.isoformat(), "status": "ok"},
        )

    def fake_command(command):
        command_calls.append(command)
        step = (
            "daily_backup"
            if "tools/backup/backup_pm25_data.py" in command
            else "cams_collection"
        )
        return maybe_fail(
            step,
            {"command": command, "return_code": 0},
        )

    def fake_prepare(root, active_config):
        return maybe_fail("canonical_prepare_qc", {"rows": 1})

    def fake_hardware(frame, *, config, trace_path, state_path):
        maybe_fail("hardware_aligned", None)
        state = module.read_pipeline_state(state_path) or {
            "last_successful_raw_timestamp": None,
            "last_reconciliation": None,
            "last_backup": None,
            "last_alpha_evaluation": None,
        }
        module.write_json_atomic(state_path, state)
        return {"rows_processed": 1}

    def fake_latest(trace_path, output_dir):
        return maybe_fail("latest_snapshot", {"latest": "ok"})

    def fake_alpha(frame, *, config, output_dir):
        return maybe_fail(
            "weekly_alpha_evaluation",
            {"status": "evaluated", "candidate": 3},
        )

    monkeypatch.setattr(module, "run_collector", fake_collector)
    monkeypatch.setattr(module, "_run_command", fake_command)
    monkeypatch.setattr(module, "prepare_canonical_data", fake_prepare)
    monkeypatch.setattr(module, "process_hardware_timeline", fake_hardware)
    monkeypatch.setattr(module, "make_latest_snapshot", fake_latest)
    monkeypatch.setattr(module, "evaluate_alpha_candidates", fake_alpha)
    return config, reconcile_flags, command_calls


@pytest.mark.parametrize(
    "failed_step",
    [
        "purpleair_collection",
        "cams_collection",
        "canonical_prepare_qc",
        "hardware_aligned",
        "latest_snapshot",
        "daily_backup",
        "weekly_alpha_evaluation",
    ],
)
def test_failure_preserves_steps_due_flags_log_and_redacts_secret(
    failed_step,
    tmp_path,
    monkeypatch,
):
    module = _load_module(f"unified_failure_{failed_step}")
    _install_success_fakes(
        module,
        tmp_path,
        monkeypatch,
        fail_step=failed_step,
    )
    argv = ["--now", "2026-07-30T16:00:00Z"]
    if failed_step == "daily_backup":
        argv.append("--skip-alpha-evaluation")
    elif failed_step == "weekly_alpha_evaluation":
        argv.append("--skip-backup")
    else:
        argv.extend(["--skip-backup", "--skip-alpha-evaluation"])

    assert module.main(argv) == 1

    status = json.loads(module.STATUS_PATH.read_text(encoding="utf-8"))
    steps = status["steps"]
    failed = [step for step in steps if step["status"] == "failed"]
    assert status["status"] == "failed"
    assert status["ended_at_utc"]
    assert failed[-1]["name"] == failed_step
    assert steps[-1]["name"] == failed_step
    assert status["due"]["reconciliation"] is True
    assert isinstance(status["due"]["backup"], bool)
    assert isinstance(status["due"]["alpha_evaluation"], bool)

    log_path = module.LOG_DIR / "unified_pipeline_20260730.log"
    log_lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 1
    assert json.loads(log_lines[0])["status"] == "failed"

    public_text = "\n".join(
        [
            module.STATUS_PATH.read_text(encoding="utf-8"),
            module.STATUS_REPORT.read_text(encoding="utf-8"),
            log_path.read_text(encoding="utf-8"),
        ]
    )
    assert "unit-secret" not in public_text
    assert "[REDACTED]" in public_text


def test_failed_backup_retries_across_invocations_without_reconciliation_repeat(
    tmp_path,
    monkeypatch,
):
    module = _load_module("unified_backup_retry")
    config, reconcile_flags, command_calls = _install_success_fakes(
        module,
        tmp_path,
        monkeypatch,
    )
    monkeypatch.setattr(module, "load_config", lambda path: config)
    backup_calls = 0
    original_command = module._run_command

    def fail_twice_then_succeed(command):
        nonlocal backup_calls
        if "tools/backup/backup_pm25_data.py" in command:
            backup_calls += 1
            command_calls.append(command)
            if backup_calls <= 2:
                raise RuntimeError("simulated backup failure")
            return {"command": command, "return_code": 0}
        return original_command(command)

    monkeypatch.setattr(module, "_run_command", fail_twice_then_succeed)

    first = module.main(
        ["--now", "2026-07-30T16:00:00Z", "--skip-alpha-evaluation"]
    )
    state_path = tmp_path / config["hardware_aligned"]["state_json"]
    state_after_first = json.loads(state_path.read_text(encoding="utf-8"))
    second = module.main(
        ["--now", "2026-07-30T16:15:00Z", "--skip-alpha-evaluation"]
    )
    state_after_second = json.loads(state_path.read_text(encoding="utf-8"))
    third = module.main(
        ["--now", "2026-07-30T16:30:00Z", "--skip-alpha-evaluation"]
    )
    state_after_third = json.loads(state_path.read_text(encoding="utf-8"))

    assert (first, second, third) == (1, 1, 0)
    assert reconcile_flags == [True, False, False]
    assert backup_calls == 3
    assert state_after_first["last_reconciliation"] == "2026-07-30T16:00:00+00:00"
    assert state_after_first.get("last_backup") is None
    assert state_after_second.get("last_backup") is None
    assert state_after_third["last_reconciliation"] == "2026-07-30T16:00:00+00:00"
    assert state_after_third["last_backup"] == "2026-07-30T16:30:00+00:00"

    log_path = module.LOG_DIR / "unified_pipeline_20260730.log"
    statuses = [
        json.loads(line)["status"]
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert statuses == ["failed", "failed", "ok"]


def test_no_reconciliation_and_explicit_skip_never_run_backup(
    tmp_path,
    monkeypatch,
):
    module = _load_module("unified_backup_skip")
    config, _, command_calls = _install_success_fakes(
        module,
        tmp_path,
        monkeypatch,
    )

    assert module.main(
        [
            "--offline",
            "--now",
            "2026-07-30T16:00:00Z",
            "--skip-alpha-evaluation",
        ]
    ) == 0
    first_status = json.loads(module.STATUS_PATH.read_text(encoding="utf-8"))
    assert first_status["steps"][-2] == {
        "name": "daily_backup",
        "status": "skipped",
        "reason": "no_successful_reconciliation",
    }

    assert module.main(
        [
            "--offline",
            "--now",
            "2026-07-30T17:00:00Z",
            "--skip-backup",
            "--skip-alpha-evaluation",
        ]
    ) == 0
    second_status = json.loads(module.STATUS_PATH.read_text(encoding="utf-8"))
    assert second_status["steps"][-2] == {
        "name": "daily_backup",
        "status": "skipped",
        "reason": "--skip-backup",
    }
    assert not any(
        "tools/backup/backup_pm25_data.py" in command
        for command in command_calls
    )


def test_backup_decision_persisted_timestamp_rules():
    module = _load_module("unified_backup_decision")
    now = datetime(2026, 7, 30, 16, 0, tzinfo=timezone.utc)
    interval = timedelta(hours=24)

    no_reconciliation = module.backup_decision(
        {},
        now,
        interval,
        skip_backup=False,
    )
    assert no_reconciliation["needed"] is True
    assert no_reconciliation["eligible"] is False

    newer_reconciliation = module.backup_decision(
        {
            "last_reconciliation": "2026-07-30T15:00:00Z",
            "last_backup": "2026-07-30T14:00:00Z",
        },
        now,
        interval,
        skip_backup=False,
    )
    assert newer_reconciliation["interval_due"] is False
    assert newer_reconciliation["needed"] is True
    assert newer_reconciliation["eligible"] is True
    assert newer_reconciliation["reason"] == "reconciliation_newer_than_last_backup"

    already_backed_up = module.backup_decision(
        {
            "last_reconciliation": "2026-07-30T14:00:00Z",
            "last_backup": "2026-07-30T15:00:00Z",
        },
        now,
        interval,
        skip_backup=False,
    )
    assert already_backed_up["needed"] is False
    assert already_backed_up["eligible"] is False

    explicitly_skipped = module.backup_decision(
        {
            "last_reconciliation": "2026-07-30T15:00:00Z",
            "last_backup": "2026-07-30T14:00:00Z",
        },
        now,
        interval,
        skip_backup=True,
    )
    assert explicitly_skipped["eligible"] is False
    assert explicitly_skipped["reason"] == "--skip-backup"
