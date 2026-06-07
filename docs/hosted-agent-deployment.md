# Hosted Agent Container Deployment

The hackathon starter guidance mentions a hosted-agent pattern where custom agent code is packaged as a container image, pushed to Azure Container Registry, and connected to Foundry Agent Service. This repo now includes the container image and API surface for that path, while keeping local Streamlit as the primary demo.

## Local Hosted-Agent API

Run the API without Docker:

```powershell
.\scripts\run_hosted_api.ps1 -Port 8000
```

Endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Returns service status, requested/effective mode, retrieval mode, and live config readiness |
| `POST /invoke` | Runs `run_demo_workflow(...)` and returns the `WorkflowResult` JSON |

Example request:

```powershell
$body = @{
  learner_id = "L-1001"
  selected_lab_id = "LAB-SOC-001"
  demo_response_profile = "conditional"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/invoke -Body $body -ContentType "application/json"
```

## Build And Run The Container

```powershell
.\scripts\build_hosted_agent_image.ps1 -ImageName reasoning-cyber-certification-agent -Tag v0.8.0-phase8
.\scripts\run_hosted_agent_container.ps1 -ImageName reasoning-cyber-certification-agent -Tag v0.8.0-phase8 -Port 8000 -Background
Invoke-RestMethod http://127.0.0.1:8000/health
```

The image does not contain credentials. Live Foundry settings are supplied at runtime through environment variables and `DefaultAzureCredential`-compatible hosting identity.

## Push To Azure Container Registry

```powershell
az login
.\scripts\push_acr_image.ps1 -RegistryName <acr-name> -ImageName reasoning-cyber-certification-agent -Tag v0.8.0-phase8
```

The script resolves `<acr-name>.azurecr.io`, logs in with Azure CLI, tags the local image, and pushes it.

## Connect To Foundry Agent Service

In Foundry Agent Service, create a hosted agent or custom-code agent using the pushed container image. Configure:

- Container image: `<acr-login-server>/reasoning-cyber-certification-agent:v0.8.0-phase8`
- Port: `8000`
- Health path: `/health`
- Invocation path: `/invoke`
- Identity: managed identity or platform-assigned identity with access to the Foundry project, model deployment, and knowledge base
- Environment variables: the same `APP_MODE`, `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT`, `AZURE_AI_SEARCH_ENDPOINT`, and `FOUNDRY_IQ_KNOWLEDGE_BASE` values used locally

The hosted service should call the same deterministic fallback paths if model or retrieval calls fail. Do not bake secrets into the image.

## References

- [Configure and publish Microsoft Foundry agent endpoints](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/configure-agent)
- [Configure environment and RBAC for Foundry agents](https://learn.microsoft.com/en-us/azure/foundry/agents/environment-setup)
- [Authenticate with Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-authentication)
- [Azure Container Registry image tag versioning](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-image-tag-version)
