[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet("Install", "Status", "Run", "Uninstall")]
    [string]$Action = "Status",
    [switch]$DryRun,
    [switch]$MigrateLegacyTasks,
    [switch]$WakeToRun
)

$ErrorActionPreference = "Stop"

$TaskName = "PM25 Unified Pipeline"
$LegacyTaskNames = @(
    "PM25 Backup to Drive",
    "PM25 Hourly Update",
    "PM25 Incremental Update"
)
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $ProjectRoot "tools\data_collection\run_unified_pipeline.py"

function Get-TaskIfPresent {
    param([Parameter(Mandatory = $true)][string]$Name)
    Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
}

function Show-TaskStatus {
    param([Parameter(Mandatory = $true)][string]$Name)
    $Task = Get-TaskIfPresent -Name $Name
    if ($null -eq $Task) {
        [pscustomobject]@{
            TaskName = $Name
            Installed = $false
            State = "NotInstalled"
            LastRunTime = $null
            LastTaskResult = $null
            NextRunTime = $null
        }
        return
    }
    $Info = Get-ScheduledTaskInfo -TaskName $Name
    [pscustomobject]@{
        TaskName = $Name
        Installed = $true
        State = [string]$Task.State
        LastRunTime = $Info.LastRunTime
        LastTaskResult = $Info.LastTaskResult
        NextRunTime = $Info.NextRunTime
    }
}

function Assert-LocalRuntime {
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        throw "Missing Python environment: $PythonExe"
    }
    if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
        throw "Missing unified runner: $Runner"
    }
}

function Get-XmlNodeText {
    param(
        [Parameter(Mandatory = $true)][xml]$Xml,
        [Parameter(Mandatory = $true)][string]$XPath
    )
    $Node = $Xml.SelectSingleNode($XPath)
    if ($null -eq $Node) {
        return $null
    }
    return [string]$Node.InnerText
}

function Assert-UnifiedTaskRegistration {
    param(
        [Parameter(Mandatory = $true)][string]$ExpectedPython,
        [Parameter(Mandatory = $true)][string]$ExpectedRunner,
        [Parameter(Mandatory = $true)][string]$ExpectedWorkingDirectory
    )

    $Registered = Get-TaskIfPresent -Name $TaskName
    if ($null -eq $Registered) {
        throw "Scheduled task '$TaskName' was not found after registration."
    }

    [xml]$TaskXml = Export-ScheduledTask -TaskName $TaskName
    $Command = Get-XmlNodeText -Xml $TaskXml -XPath "//*[local-name()='Actions']/*[local-name()='Exec']/*[local-name()='Command']"
    $Arguments = Get-XmlNodeText -Xml $TaskXml -XPath "//*[local-name()='Actions']/*[local-name()='Exec']/*[local-name()='Arguments']"
    $WorkingDirectory = Get-XmlNodeText -Xml $TaskXml -XPath "//*[local-name()='Actions']/*[local-name()='Exec']/*[local-name()='WorkingDirectory']"
    $Interval = Get-XmlNodeText -Xml $TaskXml -XPath "//*[local-name()='Triggers']/*/*[local-name()='Repetition']/*[local-name()='Interval']"
    $Duration = Get-XmlNodeText -Xml $TaskXml -XPath "//*[local-name()='Triggers']/*/*[local-name()='Repetition']/*[local-name()='Duration']"
    $MultipleInstances = Get-XmlNodeText -Xml $TaskXml -XPath "//*[local-name()='Settings']/*[local-name()='MultipleInstancesPolicy']"
    $RestartCount = Get-XmlNodeText -Xml $TaskXml -XPath "//*[local-name()='Settings']/*[local-name()='RestartOnFailure']/*[local-name()='Count']"

    if (-not [string]::Equals($Command, $ExpectedPython, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Registered task command mismatch. Expected '$ExpectedPython', got '$Command'."
    }
    if ([string]::IsNullOrWhiteSpace($Arguments) -or $Arguments.IndexOf($ExpectedRunner, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "Registered task arguments do not contain the unified runner '$ExpectedRunner'."
    }
    if (-not [string]::Equals($WorkingDirectory, $ExpectedWorkingDirectory, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Registered task working-directory mismatch."
    }
    if ($Interval -ne "PT1H") {
        throw "Registered task repetition interval is '$Interval', expected 'PT1H'."
    }
    if (-not [string]::IsNullOrWhiteSpace($Duration)) {
        throw "Registered task unexpectedly has a finite repetition duration '$Duration'."
    }
    if ($MultipleInstances -ne "IgnoreNew") {
        throw "Registered task overlap policy is '$MultipleInstances', expected 'IgnoreNew'."
    }
    if ($RestartCount -ne "3") {
        throw "Registered task restart count is '$RestartCount', expected '3'."
    }
}

if ($Action -eq "Status") {
    Show-TaskStatus -Name $TaskName
    foreach ($LegacyName in $LegacyTaskNames) {
        $Legacy = Get-TaskIfPresent -Name $LegacyName
        if ($null -ne $Legacy) {
            Write-Warning "Legacy PM2.5 task is still installed: $LegacyName"
            Show-TaskStatus -Name $LegacyName
        }
    }
    exit 0
}

if ($Action -eq "Uninstall") {
    $Existing = Get-TaskIfPresent -Name $TaskName
    if ($null -eq $Existing) {
        Write-Host "Task is not installed: $TaskName"
        exit 0
    }
    if ($DryRun) {
        Write-Host "DRY RUN: would unregister scheduled task '$TaskName'."
        exit 0
    }
    if ($PSCmdlet.ShouldProcess($TaskName, "Unregister scheduled task")) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Uninstalled scheduled task '$TaskName'."
    }
    exit 0
}

Assert-LocalRuntime

if ($Action -eq "Run") {
    if ([string]::IsNullOrWhiteSpace($env:PURPLEAIR_API_KEY)) {
        throw "PURPLEAIR_API_KEY is not available to this process."
    }
    if ($DryRun) {
        & $PythonExe $Runner --dry-run
    }
    else {
        & $PythonExe $Runner
    }
    exit $LASTEXITCODE
}

$PresentLegacyTasks = @(
    foreach ($LegacyName in $LegacyTaskNames) {
        if ($null -ne (Get-TaskIfPresent -Name $LegacyName)) {
            $LegacyName
        }
    }
)
if ($PresentLegacyTasks.Count -gt 0 -and -not $MigrateLegacyTasks) {
    $Names = $PresentLegacyTasks -join "', '"
    throw "Legacy PM2.5 task(s) found: '$Names'. Re-run Install with -MigrateLegacyTasks after reviewing them so only the unified task remains."
}

$StartAt = (Get-Date).AddMinutes(1)
$TaskAction = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument ('"{0}"' -f $Runner) `
    -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Once -At $StartAt `
    -RepetitionInterval (New-TimeSpan -Hours 1)
# A repetition pattern with no Duration and no EndBoundary is indefinite.
$Trigger.Repetition.Duration = $null
$Trigger.Repetition.StopAtDurationEnd = $false
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 15) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 55) `
    -WakeToRun:$WakeToRun
$CurrentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal = New-ScheduledTaskPrincipal `
    -UserId $CurrentIdentity `
    -LogonType Interactive `
    -RunLevel Limited

if ($DryRun -or $WhatIfPreference) {
    Write-Host "DRY RUN/WHATIF: would install/update '$TaskName'."
    Write-Host "  Python: $PythonExe"
    Write-Host "  Runner: $Runner"
    Write-Host "  Working directory: $ProjectRoot"
    Write-Host "  Trigger: hourly and indefinite, first run $StartAt"
    Write-Host "  Repetition: interval PT1H; duration omitted; StopAtDurationEnd false"
    Write-Host "  Retry: 3 times at 15-minute intervals"
    Write-Host "  StartWhenAvailable: true; overlapping instances: ignored"
    Write-Host "  WakeToRun: $([bool]$WakeToRun) (opt-in only)"
    foreach ($LegacyName in $PresentLegacyTasks) {
        Write-Host "  Would temporarily disable legacy task: $LegacyName"
    }
    Write-Host "  Would register and verify the unified task before removing any legacy task."
    foreach ($LegacyName in $PresentLegacyTasks) {
        Write-Host "  Would unregister legacy task only after unified-task verification: $LegacyName"
    }
    exit 0
}

$ExistingUnifiedXml = $null
if ($null -ne (Get-TaskIfPresent -Name $TaskName)) {
    $ExistingUnifiedXml = Export-ScheduledTask -TaskName $TaskName
}
$LegacySnapshots = @()
foreach ($LegacyName in $PresentLegacyTasks) {
    $LegacyTask = Get-TaskIfPresent -Name $LegacyName
    $LegacySnapshots += [pscustomobject]@{
        Name = $LegacyName
        WasEnabled = [bool]$LegacyTask.Settings.Enabled
        Xml = Export-ScheduledTask -TaskName $LegacyName
    }
}

try {
    foreach ($Snapshot in $LegacySnapshots) {
        if ($Snapshot.WasEnabled -and $PSCmdlet.ShouldProcess($Snapshot.Name, "Temporarily disable legacy PM2.5 task")) {
            Disable-ScheduledTask -TaskName $Snapshot.Name | Out-Null
        }
    }

    if ($PSCmdlet.ShouldProcess($TaskName, "Install or update unified scheduled task")) {
        Register-ScheduledTask `
            -TaskName $TaskName `
            -Action $TaskAction `
            -Trigger $Trigger `
            -Settings $Settings `
            -Principal $Principal `
            -Description "Hourly PM2.5 collection, QC, hardware-aligned processing, reconciliation, backup, and candidate evaluation." `
            -Force | Out-Null
    }

    Assert-UnifiedTaskRegistration `
        -ExpectedPython $PythonExe `
        -ExpectedRunner $Runner `
        -ExpectedWorkingDirectory $ProjectRoot

    foreach ($Snapshot in $LegacySnapshots) {
        if ($PSCmdlet.ShouldProcess($Snapshot.Name, "Unregister verified legacy PM2.5 task")) {
            Unregister-ScheduledTask -TaskName $Snapshot.Name -Confirm:$false
        }
    }
}
catch {
    $InstallError = $_
    Write-Warning "Unified-task migration failed; attempting rollback."

    try {
        if ($null -ne $ExistingUnifiedXml) {
            Register-ScheduledTask -TaskName $TaskName -Xml $ExistingUnifiedXml -Force | Out-Null
        }
        elseif ($null -ne (Get-TaskIfPresent -Name $TaskName)) {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        }
    }
    catch {
        Write-Warning "Could not fully restore the previous unified task: $($_.Exception.Message)"
    }

    foreach ($Snapshot in $LegacySnapshots) {
        try {
            if ($null -eq (Get-TaskIfPresent -Name $Snapshot.Name)) {
                Register-ScheduledTask -TaskName $Snapshot.Name -Xml $Snapshot.Xml -Force | Out-Null
            }
            if ($Snapshot.WasEnabled) {
                Enable-ScheduledTask -TaskName $Snapshot.Name | Out-Null
            }
            else {
                Disable-ScheduledTask -TaskName $Snapshot.Name | Out-Null
            }
        }
        catch {
            Write-Warning "Could not fully restore legacy task '$($Snapshot.Name)': $($_.Exception.Message)"
        }
    }

    throw $InstallError
}

Show-TaskStatus -Name $TaskName
Write-Host "The task reads PURPLEAIR_API_KEY from the environment of the task account; the key is not stored in this task definition."
