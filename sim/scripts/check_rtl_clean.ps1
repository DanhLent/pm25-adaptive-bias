[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$Files = @(
    Get-ChildItem -LiteralPath (Join-Path $Root "rtl\core") -File -Include *.v,*.vh
    Get-ChildItem -LiteralPath (Join-Path $Root "rtl\apb") -File -Include *.v,*.vh
    Get-ChildItem -LiteralPath (Join-Path $Root "rtl\uart") -File -Include *.v,*.vh
    Get-ChildItem -LiteralPath (Join-Path $Root "rtl\top") -File -Include *.v,*.vh
)
if ($Files.Count -eq 0) {
    throw "[pm25] clean-rtl: FAIL no RTL files found"
}

$Forbidden = @(
    @{ Name = "simulation system task"; Pattern = '\$(display|readmemh|fopen|fscanf|finish)\b' },
    @{ Name = "initial block"; Pattern = '(?m)(^|\s)initial(\s|$)' },
    @{ Name = "simulation delay"; Pattern = '#\s*[0-9]' }
)
$Errors = @()
foreach ($File in $Files) {
    $Text = Get-Content -LiteralPath $File.FullName -Raw
    foreach ($Rule in $Forbidden) {
        if ($Text -match $Rule.Pattern) {
            $Errors += "$($File.FullName): $($Rule.Name)"
        }
    }
}
if ($Errors.Count -gt 0) {
    $Errors | ForEach-Object { Write-Error $_ }
    throw "[pm25] clean-rtl: FAIL"
}
Write-Host "[pm25] clean-rtl: PASS"
