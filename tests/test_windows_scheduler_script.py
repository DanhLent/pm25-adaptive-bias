from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/windows/manage_pm25_unified_task.ps1"


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_scheduler_script_has_required_single_task_safety_settings():
    text = _text()

    assert '$TaskName = "PM25 Unified Pipeline"' in text
    assert "-RepetitionInterval (New-TimeSpan -Hours 1)" in text
    assert "$Trigger.Repetition.Duration = $null" in text
    assert "$Trigger.Repetition.StopAtDurationEnd = $false" in text
    assert "-RestartCount 3" in text
    assert "-RestartInterval (New-TimeSpan -Minutes 15)" in text
    assert "-StartWhenAvailable" in text
    assert "-MultipleInstances IgnoreNew" in text
    assert "PURPLEAIR_API_KEY" in text
    assert "api_key=" not in text.lower()
    assert "Start-ScheduledTask" not in text


def test_scheduler_action_uses_absolute_local_runtime_and_unified_runner():
    text = _text()

    assert '".venv\\Scripts\\python.exe"' in text
    assert '"tools\\data_collection\\run_unified_pipeline.py"' in text
    assert "-WorkingDirectory $ProjectRoot" in text
    assert "MigrateLegacyTasks" in text
    assert '[switch]$WakeToRun' in text
    assert "-WakeToRun:$WakeToRun" in text


def test_status_and_uninstall_do_not_require_local_venv_or_runner():
    text = _text()

    status = text.index('if ($Action -eq "Status")')
    uninstall = text.index('if ($Action -eq "Uninstall")')
    runtime_check = text.index("\nAssert-LocalRuntime\n")
    run = text.index('if ($Action -eq "Run")')
    assert status < uninstall < runtime_check < run


def test_scheduler_migration_registers_and_verifies_before_legacy_removal():
    text = _text()

    dry_run = text.index('Write-Host "DRY RUN/WHATIF: would install/update')
    register = text.index("Register-ScheduledTask `", dry_run)
    verify = text.index("Assert-UnifiedTaskRegistration `", register)
    legacy_unregister = text.index(
        "Unregister-ScheduledTask -TaskName $Snapshot.Name", verify
    )
    assert dry_run < register < verify < legacy_unregister
    assert "Disable-ScheduledTask -TaskName $Snapshot.Name" in text
    assert "Enable-ScheduledTask -TaskName $Snapshot.Name" in text
    assert "Xml = Export-ScheduledTask -TaskName $LegacyName" in text
    assert "Register-ScheduledTask -TaskName $Snapshot.Name -Xml $Snapshot.Xml -Force" in text
    assert "Unified-task migration failed; attempting rollback." in text
    assert "if ($PresentLegacyTasks.Count -gt 0 -and -not $MigrateLegacyTasks)" in text


def test_scheduler_registration_verification_checks_critical_xml_contract():
    text = _text()

    assert "Export-ScheduledTask -TaskName $TaskName" in text
    assert "Registered task command mismatch" in text
    assert "expected 'PT1H'" in text
    assert "finite repetition duration" in text
    assert "expected 'IgnoreNew'" in text
    assert "expected '3'" in text
