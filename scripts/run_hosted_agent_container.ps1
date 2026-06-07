param(
    [string]$ImageName = "reasoning-cyber-certification-agent",
    [string]$Tag = "local",
    [int]$Port = 8000,
    [string]$ContainerName = "reasoning-cyber-certification-agent",
    [switch]$Background
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is required to run the hosted agent container."
}

$EnvNames = @(
    "APP_MODE",
    "AZURE_AI_PROJECT_ENDPOINT",
    "AZURE_AI_MODEL_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_AI_SEARCH_ENDPOINT",
    "FOUNDRY_IQ_KNOWLEDGE_BASE",
    "FOUNDRY_IQ_API_VERSION",
    "FOUNDRY_IQ_MAX_DOCS",
    "FOUNDRY_IQ_MAX_OUTPUT_TOKENS"
)
$EnvArgs = @("-e", "HOSTED_AGENT_API_PORT=8000")
foreach ($Name in $EnvNames) {
    $Value = [Environment]::GetEnvironmentVariable($Name)
    if ($Value) {
        $EnvArgs += @("-e", "$Name=$Value")
    }
}

$RunArgs = @("run", "--rm", "-p", "$Port`:8000")
if ($Background) {
    $RunArgs += @("-d", "--name", $ContainerName)
}
$RunArgs += $EnvArgs
$RunArgs += "$ImageName`:$Tag"

& docker @RunArgs
if ($Background) {
    Write-Host "Hosted agent container running at http://127.0.0.1:$Port"
}
