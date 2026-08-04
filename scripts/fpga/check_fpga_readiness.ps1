[CmdletBinding()]
param(
    [string]$Device,
    [string]$ConstraintFile
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

[ordered]@{
    project_root = $ProjectRoot
    planned_board_from_repository = "Tang Nano 9K"
    exact_device_supplied = -not [string]::IsNullOrWhiteSpace($Device)
    exact_device = $Device
    gowin_shell_found = $null -ne $Gowin
    gowin_shell = if ($null -ne $Gowin) { $Gowin.Source } else { $null }
    verified_constraint_supplied = $ConstraintExists -and -not $ConstraintIsTemplate
    constraint_file = $ConstraintFile
    physical_board_status = "UNVERIFIED ON PHYSICAL BOARD"
    core_synthesis_ready = ($null -ne $Gowin) -and -not [string]::IsNullOrWhiteSpace($Device)
    uart_implementation_ready = (
        ($null -ne $Gowin) -and
        -not [string]::IsNullOrWhiteSpace($Device) -and
        $ConstraintExists -and
        -not $ConstraintIsTemplate
    )
} | ConvertTo-Json
