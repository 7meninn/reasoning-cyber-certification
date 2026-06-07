param(
    [string]$ImageName = "reasoning-cyber-certification-agent",
    [string]$Tag = "local"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is required to build the hosted agent image."
}

& docker build -t "$ImageName`:$Tag" -f (Join-Path $ProjectRoot "Dockerfile") $ProjectRoot
Write-Host "Built image $ImageName`:$Tag"
