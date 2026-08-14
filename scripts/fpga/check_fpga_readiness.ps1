[CmdletBinding()]
param(
    [string]$Device,
    [string]$ConstraintFile,
    [string]$TimingConstraintFile,
    [string]$HardwareEvidenceReport = "reports\fpga\hardware_validation.json"
)

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$Gowin = Get-Command "gw_sh.exe" -ErrorAction SilentlyContinue
if ($null -eq $Gowin) {
    $Gowin = Get-Command "gw_sh" -ErrorAction SilentlyContinue
}
$ConstraintExists = $false
$ConstraintIsTemplate = $false
if ($ConstraintFile) {
    $ConstraintExists = Test-Path -LiteralPath $ConstraintFile -PathType Leaf
    $ConstraintIsTemplate = $ConstraintFile.EndsWith(
        ".template",
        [StringComparison]::OrdinalIgnoreCase
    )
}
$TimingConstraintExists = $false
$TimingConstraintIsTemplate = $false
if ($TimingConstraintFile) {
    $TimingConstraintExists = Test-Path -LiteralPath $TimingConstraintFile -PathType Leaf
    $TimingConstraintIsTemplate = $TimingConstraintFile.EndsWith(
        ".template",
        [StringComparison]::OrdinalIgnoreCase
    )
}
$EvidencePath = Join-Path $ProjectRoot $HardwareEvidenceReport
$HardwareEvidenceExists = Test-Path -LiteralPath $EvidencePath -PathType Leaf

[ordered]@{
    project_root = $ProjectRoot
    planned_board_from_repository = "Tang Nano 9K"
    source_of_truth = "tracked rtl/, rtl/constraints/, sim/, tb/, tests/"
    local_generated_workspace = "build/gowin_gui is ignored/local and is not authoritative"
    exact_device_supplied = -not [string]::IsNullOrWhiteSpace($Device)
    exact_device = $Device
    gowin_shell_found = $null -ne $Gowin
    gowin_shell = if ($null -ne $Gowin) { $Gowin.Source } else { $null }
    board_constraint_supplied = $ConstraintExists -and -not $ConstraintIsTemplate
    constraint_file = $ConstraintFile
    timing_constraint_supplied = $TimingConstraintExists -and -not $TimingConstraintIsTemplate
    timing_constraint_file = $TimingConstraintFile
    simulation_readiness = "Use pytest and sim/scripts/run_all_tests.ps1 for local non-hardware regression."
    synthesis_readiness = ($null -ne $Gowin) -and -not [string]::IsNullOrWhiteSpace($Device)
    implementation_readiness = (
        ($null -ne $Gowin) -and
        -not [string]::IsNullOrWhiteSpace($Device) -and
        $ConstraintExists -and
        -not $ConstraintIsTemplate -and
        $TimingConstraintExists -and
        -not $TimingConstraintIsTemplate
    )
    preserved_hardware_validation_evidence = $HardwareEvidenceExists
    hardware_validation_evidence_report = $HardwareEvidenceReport
    hardware_validation_note = "Hardware validation is preserved by explicit evidence reports/logs, not inferred from parser output or readiness inputs."
    core_synthesis_ready = ($null -ne $Gowin) -and -not [string]::IsNullOrWhiteSpace($Device)
    uart_implementation_ready = (
        ($null -ne $Gowin) -and
        -not [string]::IsNullOrWhiteSpace($Device) -and
        $ConstraintExists -and
        -not $ConstraintIsTemplate -and
        $TimingConstraintExists -and
        -not $TimingConstraintIsTemplate
    )
} | ConvertTo-Json
