[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Core", "UartTop")]
    [string]$Target,
    [Parameter(Mandatory = $true)]
    [string]$Device,
    [string]$ConstraintFile,
    [string]$TimingConstraintFile,
    [string]$GowinShell,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$TclScript = Join-Path $PSScriptRoot "gowin_build.tcl"
$Top = if ($Target -eq "Core") { "pm25_alert_core" } else { "pm25_uart_demo_top" }
$Flow = if ($Target -eq "Core") { "syn" } else { "all" }
$BuildDir = Join-Path $ProjectRoot ("build\gowin\" + $Target.ToLowerInvariant())

if ([string]::IsNullOrWhiteSpace($Device)) {
    throw "Exact Gowin device/part is required; no board part is guessed."
}
if ($Target -eq "UartTop") {
    if ([string]::IsNullOrWhiteSpace($ConstraintFile)) {
        throw "UartTop requires a verified .cst file."
    }
    $ConstraintFile = (Resolve-Path -LiteralPath $ConstraintFile).Path
    if ($ConstraintFile.EndsWith(".template", [StringComparison]::OrdinalIgnoreCase)) {
        throw "A constraint template cannot be used for implementation."
    }
    if ([IO.Path]::GetExtension($ConstraintFile) -ne ".cst") {
        throw "UartTop constraint must be a verified .cst file."
    }
}
if ($TimingConstraintFile) {
    $TimingConstraintFile = (Resolve-Path -LiteralPath $TimingConstraintFile).Path
    if ($TimingConstraintFile.EndsWith(".template", [StringComparison]::OrdinalIgnoreCase)) {
        throw "A timing-constraint template cannot be used for implementation."
    }
}

if (-not $GowinShell) {
    $Command = Get-Command "gw_sh.exe" -ErrorAction SilentlyContinue
    if ($null -eq $Command) {
        $Command = Get-Command "gw_sh" -ErrorAction SilentlyContinue
    }
    if ($null -ne $Command) {
        $GowinShell = $Command.Source
    }
}

$Plan = [ordered]@{
    target = $Target
    top = $Top
    exact_device = $Device
    flow = $Flow
    build_directory = $BuildDir
    constraint_file = $ConstraintFile
    timing_constraint_file = $TimingConstraintFile
    gowin_shell = $GowinShell
    verified_on_physical_board = $false
}
if ($DryRun) {
    $Plan | ConvertTo-Json
    exit 0
}
if ([string]::IsNullOrWhiteSpace($GowinShell) -or -not (Test-Path -LiteralPath $GowinShell -PathType Leaf)) {
    throw "Gowin gw_sh was not found. Supply -GowinShell with the exact executable path."
}

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
$env:PM25_PROJECT_ROOT = $ProjectRoot
$env:PM25_GOWIN_DEVICE = $Device
$env:PM25_GOWIN_TOP = $Top
$env:PM25_GOWIN_FLOW = $Flow
$env:PM25_GOWIN_CST = if ($ConstraintFile) { $ConstraintFile } else { "" }
$env:PM25_GOWIN_SDC = if ($TimingConstraintFile) { $TimingConstraintFile } else { "" }

Push-Location $BuildDir
try {
    & $GowinShell $TclScript
    if ($LASTEXITCODE -ne 0) {
        throw "Gowin build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

& (Join-Path $ProjectRoot ".venv\Scripts\python.exe") `
    (Join-Path $ProjectRoot "tools\fpga\parse_gowin_reports.py") `
    --build-dir $BuildDir `
    --target $Target `
    --output-dir (Join-Path $ProjectRoot "reports\fpga")
exit $LASTEXITCODE
