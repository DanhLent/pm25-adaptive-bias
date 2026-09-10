param(
    [string]$Port = "COM4",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$Feeder = Join-Path $ProjectRoot "demo\uart\pm25_uart_feeder.py"
$DemoRoot = $PSScriptRoot
$LogRoot = Join-Path $DemoRoot "logs"

$WindowsVenv = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LinuxVenv = Join-Path $ProjectRoot ".venv-ubuntu24\bin\python"
if (Test-Path $WindowsVenv) {
    $Python = $WindowsVenv
} elseif (Test-Path $LinuxVenv) {
    $Python = $LinuxVenv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
} else {
    throw "Không tìm thấy Python. Hãy tạo .venv hoặc thêm python vào PATH."
}

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

function Invoke-Scenario {
    param(
        [string]$Csv,
        [int]$Limit,
        [string]$LogName
    )

    $Args = @(
        $Feeder,
        "--baud", "115200",
        "--csv", (Join-Path $DemoRoot $Csv),
        "--limit", "$Limit",
        "--alpha-shift", "3",
        "--log", (Join-Path $LogRoot $LogName)
    )
    if ($DryRun) {
        $Args += "--dry-run"
    } else {
        $Args += @("--port", $Port)
    }

    & $Python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Scenario $Csv thất bại với exit code $LASTEXITCODE"
    }
}

Write-Host "=== Lượt 1: adaptive bias, QC hold và hysteresis ===" -ForegroundColor Cyan
if (-not $DryRun) {
    Read-Host "Nhấn reset trên Tang Nano 9K, sau đó nhấn Enter"
}
Invoke-Scenario -Csv "demo_mixed_8.csv" -Limit 8 -LogName "demo_mixed_8_result.csv"

Write-Host "=== Lượt 2: bão hòa bias dương và âm ===" -ForegroundColor Cyan
if (-not $DryRun) {
    Read-Host "Nhấn reset lần nữa, sau đó nhấn Enter"
}
Invoke-Scenario -Csv "demo_saturation_4.csv" -Limit 4 -LogName "demo_saturation_4_result.csv"

Write-Host "=== HOÀN TẤT: 12 giao dịch ===" -ForegroundColor Green
