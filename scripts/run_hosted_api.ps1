param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Background
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$Python = Join-Path $VenvPath "Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"

if (-not (Test-Path $Python)) {
    python -m venv $VenvPath
}

& $Python -m pip install --disable-pip-version-check --no-input -r $Requirements

$env:PYTHONPATH = Join-Path $ProjectRoot "app\src"
$env:HOSTED_AGENT_API_HOST = $HostAddress
$env:HOSTED_AGENT_API_PORT = [string]$Port

if ($Background) {
    Start-Process `
        -FilePath $Python `
        -ArgumentList "-m cybersecurity_readiness.hosted_api" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden
    Write-Host "Hosted agent API running at http://$HostAddress`:$Port"
} else {
    & $Python -m cybersecurity_readiness.hosted_api
}
