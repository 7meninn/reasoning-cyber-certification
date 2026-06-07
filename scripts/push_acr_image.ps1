param(
    [Parameter(Mandatory = $true)]
    [string]$RegistryName,
    [string]$ImageName = "reasoning-cyber-certification-agent",
    [string]$Tag = "local"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is required. Install az CLI and run az login."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is required to tag and push the image."
}

$LoginServer = & az acr show --name $RegistryName --query loginServer -o tsv --only-show-errors
if ($LASTEXITCODE -ne 0 -or -not $LoginServer) {
    Write-Error "Could not resolve Azure Container Registry login server for $RegistryName."
}

& az acr login --name $RegistryName --only-show-errors
$RemoteImage = "$LoginServer/$ImageName`:$Tag"
& docker tag "$ImageName`:$Tag" $RemoteImage
& docker push $RemoteImage
Write-Host "Pushed $RemoteImage"
