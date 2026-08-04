$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $ProjectRoot "tools\data_collection\run_unified_pipeline.py"

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Missing Python environment: $PythonExe"
}
if ([string]::IsNullOrWhiteSpace($env:PURPLEAIR_API_KEY)) {
    throw "PURPLEAIR_API_KEY is not set in the task account environment."
}

& $PythonExe $Runner @args
exit $LASTEXITCODE
