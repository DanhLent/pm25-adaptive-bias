[CmdletBinding()]
param(
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$VenvRoot = Join-Path $Root ".venv"
$ArchiveRoot = Join-Path $Root "archive"
$Directories = @(
    Get-ChildItem -LiteralPath $Root -Recurse -Directory -Filter "__pycache__" -Force |
        Where-Object {
            -not $_.FullName.StartsWith($VenvRoot + [IO.Path]::DirectorySeparatorChar) -and
            -not $_.FullName.StartsWith($ArchiveRoot + [IO.Path]::DirectorySeparatorChar)
        }
)
foreach ($Relative in @(".pytest_cache", "sim\modelsim_work")) {
    $Candidate = Join-Path $Root $Relative
    if (Test-Path -LiteralPath $Candidate -PathType Container) {
        $Directories += Get-Item -LiteralPath $Candidate
    }
}
$Directories = @($Directories | Sort-Object FullName -Unique)

$Validated = @()
foreach ($Directory in $Directories) {
    $Resolved = (Resolve-Path -LiteralPath $Directory.FullName).Path
    if (-not $Resolved.StartsWith($Root + [IO.Path]::DirectorySeparatorChar)) {
        throw "Cleanup target escapes the workspace: $Resolved"
    }
    if ($Resolved.StartsWith($VenvRoot + [IO.Path]::DirectorySeparatorChar)) {
        throw "Refusing to clean local environment: $Resolved"
    }
    if ($Resolved.StartsWith($ArchiveRoot + [IO.Path]::DirectorySeparatorChar)) {
        throw "Refusing to clean preserved archive: $Resolved"
    }
    $Validated += $Resolved
}

$WaveDir = (Resolve-Path -LiteralPath (Join-Path $Root "sim\waves")).Path
$WaveFiles = @(
    Get-ChildItem -LiteralPath $WaveDir -File -Force |
        Where-Object { $_.Name -ne ".gitkeep" }
)
foreach ($File in $WaveFiles) {
    if (-not $File.FullName.StartsWith($WaveDir + [IO.Path]::DirectorySeparatorChar)) {
        throw "Wave cleanup target escapes sim/waves: $($File.FullName)"
    }
}

if (-not $Execute) {
    [ordered]@{
        mode = "dry_run"
        directories = $Validated
        wave_files = @($WaveFiles.FullName)
        local_venv_preserved = $true
        archive_preserved = $true
    } | ConvertTo-Json -Depth 3
    exit 0
}

foreach ($Resolved in ($Validated | Sort-Object Length -Descending)) {
    if (Test-Path -LiteralPath $Resolved) {
        Remove-Item -LiteralPath $Resolved -Recurse -Force
    }
}
foreach ($File in $WaveFiles) {
    if (Test-Path -LiteralPath $File.FullName) {
        Remove-Item -LiteralPath $File.FullName -Force
    }
}

[ordered]@{
    mode = "executed"
    removed_directories = $Validated.Count
    removed_wave_files = $WaveFiles.Count
    local_venv_preserved = Test-Path -LiteralPath $VenvRoot -PathType Container
    archive_preserved = Test-Path -LiteralPath $ArchiveRoot -PathType Container
    pytest_cache_remaining = Test-Path -LiteralPath (Join-Path $Root ".pytest_cache")
    modelsim_work_remaining = Test-Path -LiteralPath (Join-Path $Root "sim\modelsim_work")
} | ConvertTo-Json
