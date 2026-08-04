# Windows Task Scheduler: Unified PM2.5 Pipeline

Exactly one scheduled task should remain:

```text
PM25 Unified Pipeline
```

It starts once per hour, runs `tools/data_collection/run_unified_pipeline.py`, and exits. Daily reconciliation/backup and weekly alpha evaluation are due-state-controlled inside the orchestrator, not separate Windows tasks.

The hotfix session intentionally does not install or start this task. Complete
the pre-install checks and review the DryRun output before using the non-DryRun
commands below.

## 1. Rotate the removed credential

An API key had been embedded in old launchers. The source copies are now safe, but the old credential should be revoked in PurpleAir and replaced. Store the replacement in the user environment of the account that runs the task:

```powershell
[Environment]::SetEnvironmentVariable(
    "PURPLEAIR_API_KEY",
    "REPLACE_WITH_ROTATED_KEY",
    "User"
)
```

Open a new PowerShell process afterward. Do not put the key in `config.yaml`, a command argument, a batch file, or a log.

## 2. Inspect before changing tasks

Run PowerShell as the intended task user:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\windows\manage_pm25_unified_task.ps1 -Action Status
```

The manager reports the unified task and warns about known legacy tasks. This workspace audit found `PM25 Backup to Drive`; it was not automatically changed.

Preview installation and legacy migration without changing Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\windows\manage_pm25_unified_task.ps1 `
  -Action Install -MigrateLegacyTasks -DryRun
```

## 3. Reviewed install command

Do not run this non-DryRun command until Section 4 passes and the hotfix is
reviewed:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\windows\manage_pm25_unified_task.ps1 `
  -Action Install -MigrateLegacyTasks
```

`-MigrateLegacyTasks` performs a rollback-safe migration: it snapshots and temporarily disables only the known PM2.5 legacy tasks, registers the unified task, exports and verifies its command, working directory, hourly repetition, overlap policy, and retry count, and only then unregisters the legacy tasks. If registration or verification fails, the prior unified task is restored when possible and previously enabled legacy tasks are re-enabled. The verified unified task uses:

- absolute `.venv\Scripts\python.exe` and orchestrator paths;
- project root as the working directory;
- hourly `PT1H` trigger with no duration/end boundary, so repetition is indefinite;
- `StartWhenAvailable`;
- no new instance when one is already running;
- up to three retries at 15-minute intervals;
- 55-minute execution limit.

The principal uses the current interactive user with limited privileges. That account must be logged in, its user environment must contain `PURPLEAIR_API_KEY`, Google Drive must be mounted for due backups, and the PC must be on and not in deep sleep. The repository lock independently protects against overlap. Wake-from-sleep is disabled by default; add `-WakeToRun` to the reviewed Install command only if the user explicitly wants the PC to wake. Network-only task gating is not enabled because Windows network-profile detection can delay catch-up; the collectors use bounded retries and timestamp/gap-based catch-up instead.

## 4. Pre-install validation

Run these from the canonical repository in a new PowerShell process under the
intended task account. The key-presence command does not print the key:

```powershell
[bool][Environment]::GetEnvironmentVariable("PURPLEAIR_API_KEY", "User")
Test-Path .\.venv\Scripts\python.exe
.\.venv\Scripts\python.exe -m compileall src tools training python_model demo tests
.\.venv\Scripts\python.exe -m pytest -q
# For a clean rebuild of the validated Python environment:
# .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\sim\scripts\run_all_tests.ps1
.\.venv\Scripts\python.exe .\tools\data_collection\run_unified_pipeline.py `
  --offline --dry-run --skip-backup --skip-alpha-evaluation
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\windows\manage_pm25_unified_task.ps1 `
  -Action Install -MigrateLegacyTasks -DryRun
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\windows\manage_pm25_unified_task.ps1 -Action Status
```

The local source archive policy is `keep .venv locally, ignore it in Git,
exclude it from archives`. To review a clean package:

```powershell
$archivePath = Join-Path $env:TEMP "pm25_ip_source_hotfix_20260731.zip"
.\.venv\Scripts\python.exe .\tools\repository\create_clean_source_archive.py `
  --output $archivePath
```

## 5. Test and inspect

Read-only pipeline plan:

```powershell
.\.venv\Scripts\python.exe .\tools\data_collection\run_unified_pipeline.py --dry-run
```

Manual online run through the same manager:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\windows\manage_pm25_unified_task.ps1 -Action Run
```

Check:

- `data/live/status/latest_unified_pipeline_run.json`
- `reports/PM25_UNIFIED_PIPELINE_STATUS.md`
- `logs/unified_pipeline/unified_pipeline_YYYYMMDD.log`
- Task Scheduler → `PM25 Unified Pipeline` → History
- `Get-ScheduledTaskInfo -TaskName "PM25 Unified Pipeline"`

A nonzero `LastTaskResult` means the retry policy should apply. Network/API errors use only bounded internal retries. Reconciliation is marked successful only after both collectors and the local pipeline complete. Backup failure preserves the last-known-good backup `latest` and returns a process error.

`last_reconciliation` is persisted only after reconciliation plus local
canonical/hardware/latest processing succeeds. If backup then fails,
`last_backup` is unchanged. A later invocation retries backup whenever the
persisted reconciliation is newer than the last successful backup, even when
the 72-hour reconciliation is no longer due. Failed runs retain prior
successful steps and the named failing step in both status files and the daily
JSONL log.

After a reviewed non-DryRun installation, export and inspect the registered XML
instead of trusting the construction script alone:

```powershell
[xml]$taskXml = Export-ScheduledTask -TaskName "PM25 Unified Pipeline"
$ns = [System.Xml.XmlNamespaceManager]::new($taskXml.NameTable)
$ns.AddNamespace("t", "http://schemas.microsoft.com/windows/2004/02/mit/task")
$interval = $taskXml.SelectSingleNode(
  "//t:TimeTrigger/t:Repetition/t:Interval", $ns
).InnerText
$duration = $taskXml.SelectSingleNode(
  "//t:TimeTrigger/t:Repetition/t:Duration", $ns
)
$endBoundary = $taskXml.SelectSingleNode(
  "//t:TimeTrigger/t:EndBoundary", $ns
)
$restartInterval = $taskXml.SelectSingleNode(
  "//t:Settings/t:RestartOnFailure/t:Interval", $ns
).InnerText
$restartCount = $taskXml.SelectSingleNode(
  "//t:Settings/t:RestartOnFailure/t:Count", $ns
).InnerText
$multipleInstances = $taskXml.SelectSingleNode(
  "//t:Settings/t:MultipleInstancesPolicy", $ns
).InnerText
$startWhenAvailable = $taskXml.SelectSingleNode(
  "//t:Settings/t:StartWhenAvailable", $ns
).InnerText
$info = Get-ScheduledTaskInfo -TaskName "PM25 Unified Pipeline"

if ($interval -ne "PT1H") { throw "Unexpected repetition interval: $interval" }
if ($null -ne $duration) { throw "Repetition unexpectedly expires." }
if ($null -ne $endBoundary) { throw "Trigger unexpectedly has an EndBoundary." }
if ($restartInterval -ne "PT15M" -or $restartCount -ne "3") {
  throw "Unexpected restart policy."
}
if ($multipleInstances -ne "IgnoreNew") { throw "Overlap policy is not IgnoreNew." }
if ($startWhenAvailable -ne "true") { throw "StartWhenAvailable is not enabled." }
if ($null -eq $info.NextRunTime) { throw "NextRunTime is missing." }

$taskXml.Save((Join-Path $env:TEMP "PM25_Unified_Pipeline.xml"))
$info | Format-List LastRunTime,LastTaskResult,NextRunTime
```

This XML/NextRunTime verification was not performed in the hotfix session
because the real unified task was intentionally not installed.

## 6. Safe uninstall

Preview:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\windows\manage_pm25_unified_task.ps1 -Action Uninstall -DryRun
```

Remove only the unified task:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\windows\manage_pm25_unified_task.ps1 -Action Uninstall
```

Uninstalling the task does not remove data, state, logs, backups, source, or the user environment variable.
