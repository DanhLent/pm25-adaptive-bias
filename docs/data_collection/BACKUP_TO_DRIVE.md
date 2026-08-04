# Atomic PM2.5 Backup to Google Drive

Backup is invoked by the unified hourly orchestrator only when at least one
successful reconciliation is persisted and either the backup interval is due
or that reconciliation is newer than the last successful backup. A
reconciliation may have succeeded in the current invocation or an earlier
failed invocation. Do not create a separate backup Scheduled Task. The
configured destination is:

```text
G:\My Drive\PM25_Backup
```

The allowlist includes canonical PurpleAir, persistent processing state/status, interim and processed data, predictions, latest snapshots, metrics, alpha reports, config, and README. It excludes `.venv`, caches, raw PurpleAir batches, temporary files, and launchers. The destination must already exist and Google Drive Desktop must be mounted.

## Atomic layout and failure behavior

```text
PM25_Backup\
  latest\
  latest_tmp_YYYYMMDD_HHMMSS\
  latest_previous\
  snapshots\pm25_backup_YYYYMMDD_HHMMSS.zip
  manifests\manifest_YYYYMMDD_HHMMSS.json
  logs\
```

Files are copied into a unique `latest_tmp_*` directory and checksummed. A snapshot is made from that completed staging directory. Only a successful staged copy is promoted: existing `latest` is moved temporarily, staging is renamed to `latest`, and the previous copy is then removed. If copy, snapshot, or promotion fails, last-known-good `latest` remains or is rolled back and the failed staging directory is retained for diagnosis.

The unified runner updates `last_backup` only after the backup process returns
success. Backup failure returns a nonzero orchestrator result so Windows retry
can run; it does not alter the already-created local latest prediction. The
successful `last_reconciliation` remains persisted, so a retry 15 minutes
later attempts backup again without repeating the 72-hour download and
reconciliation. Repeated failures leave `last_backup` unchanged and remain
retryable. `--skip-backup` is reported as an explicit skip, not a success or
operational failure.

## Manual verification

Run directly:

```powershell
.\.venv\Scripts\python.exe .\tools\backup\backup_pm25_data.py `
  --dest "G:\My Drive\PM25_Backup"
```

Refresh `latest` without a snapshot:

```powershell
.\.venv\Scripts\python.exe .\tools\backup\backup_pm25_data.py `
  --dest "G:\My Drive\PM25_Backup" --no-snapshot
```

In the newest manifest, require:

- `status: "ok"`;
- `latest_updated: true`;
- `files_failed: 0`;
- `files_missing: 0`;
- an empty `errors` list;
- `snapshot_created: true` unless `--no-snapshot` was intentional.

## Safe stale staging audit

No `latest_tmp_*` directory is removed merely because of its name. First run the non-mutating audit:

```powershell
.\.venv\Scripts\python.exe .\tools\backup\backup_pm25_data.py `
  --dest "G:\My Drive\PM25_Backup" --audit-stale-temp --stale-days 7
```

A directory is eligible only when all conditions are proven:

- it is an immediate `latest_tmp_*` child of the exact destination;
- a matching manifest names that exact resolved path;
- the manifest status is failed;
- `latest_tmp_retained` is true;
- the directory is older than the requested age.

Preview cleanup:

```powershell
.\.venv\Scripts\python.exe .\tools\backup\backup_pm25_data.py `
  --dest "G:\My Drive\PM25_Backup" --cleanup-stale-temp --stale-days 7 --dry-run
```

After inspecting the manifest and staged contents, perform only proven cleanup by removing `--dry-run`. Unmatched, successful, recent, symlinked, or non-directory paths are never eligible.

The old `scripts/windows/run_pm25_backup.bat` remains only for manual compatibility. The one-task operational path is documented in `WINDOWS_TASK_SCHEDULER.md`.
