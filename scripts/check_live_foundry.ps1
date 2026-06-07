param(
    [switch]$RequireLive
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$Python = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    python -m venv $VenvPath
}

$env:PYTHONPATH = Join-Path $ProjectRoot "app\src"
$ConfigJson = & $Python -c "import json; from cybersecurity_readiness.config import load_runtime_config; c=load_runtime_config(); print(json.dumps({'requested_mode': c.requested_mode, 'effective_mode': c.effective_mode, 'model_mode': c.model_mode, 'retrieval_mode': c.retrieval_mode, 'fallback_reason': c.fallback_reason, 'foundry_project_configured': c.azure_ai_project_endpoint is not None, 'model_deployment_configured': c.azure_ai_model_deployment is not None, 'search_endpoint_configured': c.azure_ai_search_endpoint is not None, 'knowledge_base_configured': c.foundry_iq_knowledge_base is not None}))"
$Config = $ConfigJson | ConvertFrom-Json

Write-Host "Requested mode: $($Config.requested_mode)"
Write-Host "Effective mode: $($Config.effective_mode)"
Write-Host "Model mode: $($Config.model_mode)"
Write-Host "Retrieval mode: $($Config.retrieval_mode)"
if ($Config.fallback_reason) {
    Write-Warning $Config.fallback_reason
}

$LiveRequested = $Config.requested_mode -in @("foundry", "foundry_iq")
$LiveReady = $LiveRequested -and ($Config.requested_mode -eq $Config.effective_mode)

$Az = Get-Command az -ErrorAction SilentlyContinue
if (-not $Az) {
    if ($LiveRequested -or $RequireLive) {
        Write-Error "Azure CLI is required for live Foundry modes. Install az CLI and run az login."
    }
    Write-Host "Azure CLI not found; mock mode does not require it."
    exit 0
}

$AccountJson = & az account show --only-show-errors 2>$null
if ($LASTEXITCODE -ne 0 -or -not $AccountJson) {
    if ($LiveRequested -or $RequireLive) {
        Write-Error "Azure CLI is installed but not logged in. Run az login."
    }
    Write-Host "Azure CLI is installed but not logged in; mock mode does not require it."
    exit 0
}

$Account = $AccountJson | ConvertFrom-Json
Write-Host "Azure account: $($Account.user.name)"
Write-Host "Subscription: $($Account.name)"

if ($RequireLive -and -not $LiveReady) {
    Write-Error "Live mode requested by -RequireLive, but required Foundry configuration is incomplete."
}

if ($LiveReady) {
    Write-Host "Live Foundry configuration is ready for $($Config.effective_mode)."
} else {
    Write-Host "Live Foundry configuration is not active; app will use deterministic fallback behavior."
}
