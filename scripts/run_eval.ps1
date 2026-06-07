$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$Python = Join-Path $VenvPath "Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "requirements-test.txt"

if (-not (Test-Path $Python)) {
    python -m venv $VenvPath
}

& $Python -m pip install --disable-pip-version-check --no-input -r $Requirements
$env:PYTHONPATH = Join-Path $ProjectRoot "app\src"
& $Python -m cybersecurity_readiness.evaluation --write-reports --export-foundry
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
