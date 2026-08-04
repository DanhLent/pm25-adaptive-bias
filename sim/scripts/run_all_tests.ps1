[CmdletBinding()]
param(
    [switch]$SkipVectorGeneration
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Waves = Join-Path $Root "sim\waves"

foreach ($Tool in @("iverilog", "vvp")) {
    if ($null -eq (Get-Command $Tool -ErrorAction SilentlyContinue)) {
        throw "Required simulator executable not found on PATH: $Tool"
    }
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python environment not found: $Python"
}

Push-Location $Root
try {
    & (Join-Path $PSScriptRoot "check_rtl_clean.ps1")
    if (-not $SkipVectorGeneration) {
        & $Python "python_model/fixed_point/generate_test_vectors_v1.py"
        if ($LASTEXITCODE -ne 0) { throw "Default vector generation failed." }
        & $Python "python_model/fixed_point/generate_extra_test_vectors_v1.py"
        if ($LASTEXITCODE -ne 0) { throw "Extra vector generation failed." }
        & $Python "python_model/fixed_point/generate_alpha_shift_vectors.py"
        if ($LASTEXITCODE -ne 0) { throw "Alpha-shift vector generation failed." }
    }

    New-Item -ItemType Directory -Force -Path $Waves | Out-Null
    $CoreSources = @(
        "rtl/core/alert_classifier.v",
        "rtl/core/hysteresis.v",
        "rtl/core/bias_update.v",
        "rtl/core/fusion.v",
        "rtl/core/pm25_alert_core.v"
    )
    $DefaultImage = "sim/waves/pm25_alert_core_tb.vvp"
    & iverilog -g2012 -Wall -Wno-timescale -I rtl/core -o $DefaultImage `
        @CoreSources "tb/verilog/tb_pm25_alert_core.v"
    if ($LASTEXITCODE -ne 0) { throw "Default core compile failed." }

    $DefaultVectors = @(
        Get-ChildItem -LiteralPath "data/test_vectors" -Filter *.csv -File
        Get-ChildItem -LiteralPath "data/test_vectors/extra" -Filter *.csv -File
    )
    $VectorCount = 0
    $SampleCount = 0
    foreach ($Vector in $DefaultVectors) {
        $Relative = $Vector.FullName.Substring($Root.Length + 1).Replace("\", "/")
        $Output = & vvp $DefaultImage "+VECTOR=$Relative" "+VECTOR_NAME=$($Vector.BaseName)"
        $Output | Write-Host
        if ($LASTEXITCODE -ne 0) { throw "Core vector failed: $Relative" }
        $Match = [regex]::Match(($Output -join "`n"), 'samples=(\d+)')
        if ($Match.Success) { $SampleCount += [int]$Match.Groups[1].Value }
        $VectorCount += 1
    }

    foreach ($Shift in 2..6) {
        $Image = "sim/waves/pm25_alert_core_tb_shift_$Shift.vvp"
        & iverilog -g2012 -Wall -Wno-timescale -I rtl/core `
            -P "tb_pm25_alert_core.ALPHA_SHIFT=$Shift" `
            -o $Image @CoreSources "tb/verilog/tb_pm25_alert_core.v"
        if ($LASTEXITCODE -ne 0) { throw "ALPHA_SHIFT=$Shift compile failed." }
        $Vector = "data/test_vectors/alpha_shift/core_v1_alpha_shift_$Shift.csv"
        $Output = & vvp $Image "+VECTOR=$Vector" "+VECTOR_NAME=alpha_shift_$Shift"
        $Output | Write-Host
        if ($LASTEXITCODE -ne 0) { throw "ALPHA_SHIFT=$Shift vector failed." }
        $Match = [regex]::Match(($Output -join "`n"), 'samples=(\d+)')
        if ($Match.Success) { $SampleCount += [int]$Match.Groups[1].Value }
        $VectorCount += 1
    }

    $UartSources = @(
        "rtl/uart/uart_rx.v",
        "rtl/uart/uart_tx.v",
        "rtl/uart/pm25_packet_rx.v",
        "rtl/uart/pm25_packet_tx.v",
        "rtl/top/pm25_uart_demo_top.v"
    )
    $UartImage = "sim/waves/pm25_uart_packet_tb.vvp"
    & iverilog -g2012 -Wall -Wno-timescale -I rtl/core -I rtl/uart `
        -o $UartImage @CoreSources @UartSources "tb/verilog/tb_pm25_uart_demo_top.v"
    if ($LASTEXITCODE -ne 0) { throw "UART packet compile failed." }
    & vvp $UartImage
    if ($LASTEXITCODE -ne 0) { throw "UART packet regression failed." }

    $WrapperImage = "sim/waves/pm25_uart_wrapper_tb.vvp"
    & iverilog -g2012 -Wall -Wno-timescale -I rtl/core -I rtl/uart `
        -o $WrapperImage @CoreSources @UartSources "tb/verilog/tb_pm25_uart_wrapper.v"
    if ($LASTEXITCODE -ne 0) { throw "UART wrapper compile failed." }
    & vvp $WrapperImage
    if ($LASTEXITCODE -ne 0) { throw "UART wrapper regression failed." }

    $SerialImage = "sim/waves/pm25_uart_serial_top_tb.vvp"
    & iverilog -g2012 -Wall -Wno-timescale -I rtl/core -I rtl/uart `
        -o $SerialImage @CoreSources @UartSources "tb/verilog/tb_pm25_uart_serial_top.v"
    if ($LASTEXITCODE -ne 0) { throw "UART serial top compile failed." }
    & vvp $SerialImage
    if ($LASTEXITCODE -ne 0) { throw "UART serial top regression failed." }

    Write-Host "[pm25] complete regression: PASS vectors=$VectorCount samples=$SampleCount alpha_shifts=5 uart_packet=PASS uart_wrapper=PASS uart_serial=PASS"
}
finally {
    Pop-Location
}
