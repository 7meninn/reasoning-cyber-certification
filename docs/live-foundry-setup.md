# Live Foundry And Foundry IQ Setup

The repo is credential-free by default. A plain Azure account does not automatically make the app live; you must create or select the Foundry resources, deploy a model, create/connect the knowledge base, and set local environment variables.

## What Happens By Mode

| Mode | Required config | Runtime behavior |
|---|---|---|
| `mock` | None | Deterministic local agents and `local_mock` retrieval |
| `foundry` | Project endpoint and model deployment | Selected reasoning agents call the configured Foundry model deployment |
| `foundry_iq` | Foundry config plus Search endpoint and knowledge base | Model-backed reasoning plus live Foundry IQ retrieval |

Missing config, auth failure, malformed responses, or empty retrieval results fall back visibly to deterministic mock/local behavior and record the reason in `RunTrace`.

## Configure Azure

1. Sign in with Azure CLI:

```powershell
az login
az account show
```

2. In Microsoft Foundry, create or select a project.
3. Deploy a chat model supported by your region and quota.
4. Copy the project endpoint and deployment name.
5. Assign your signed-in identity access to the project and model deployment.

Set local environment variables directly, or copy `.env.example` to `.env` and fill in the non-secret values. The app loads `.env` automatically, and direct process environment variables override `.env` for one-off runs.

```powershell
$env:APP_MODE="foundry"
$env:AZURE_AI_PROJECT_ENDPOINT="https://<resource>.services.ai.azure.com/api/projects/<project>"
$env:AZURE_AI_MODEL_DEPLOYMENT="<deployment-name>"
.\scripts\check_live_foundry.ps1 -RequireLive
.\scripts\run_demo.ps1
```

## Configure Foundry IQ Grounding

1. Create an Azure AI Search service compatible with Foundry IQ knowledge bases.
2. Create a Foundry IQ knowledge base connected to that Search service.
3. Import only synthetic or public-summary Markdown files from `data/synthetic/knowledge_docs/upload/`.
4. Preserve source IDs, titles, URLs, snippets, and public/synthetic labels so citations remain meaningful.
5. Assign your identity permission to query the knowledge base.

If the Markdown upload pack is missing, regenerate it from the canonical JSON source list:

```powershell
.\scripts\export_knowledge_docs.ps1
```

The upload pack includes 10 small documents and a `_manifest.json` mapping each file to its source ID.

Set Foundry IQ variables:

```powershell
$env:APP_MODE="foundry_iq"
$env:AZURE_AI_PROJECT_ENDPOINT="https://<resource>.services.ai.azure.com/api/projects/<project>"
$env:AZURE_AI_MODEL_DEPLOYMENT="<deployment-name>"
$env:AZURE_AI_SEARCH_ENDPOINT="https://<search-service>.search.windows.net"
$env:FOUNDRY_IQ_KNOWLEDGE_BASE="<knowledge-base-name>"
.\scripts\check_live_foundry.ps1 -RequireLive
.\scripts\run_demo.ps1
```

When live retrieval succeeds, the UI and trace show `retrieval_mode = foundry_iq`. If it fails, the trace shows the fallback reason and the workflow continues with `local_mock`.

## Verification

Run these before demoing live mode:

```powershell
.\scripts\check_live_foundry.ps1 -RequireLive
.\scripts\run_tests.ps1
.\scripts\run_eval.ps1
```

Then open the Streamlit trace drawer and confirm:

- `requested_app_mode` is `foundry` or `foundry_iq`.
- `effective_app_mode` matches the requested mode.
- `model_mode` is `foundry`.
- `retrieval_mode` is `foundry_iq` only after live retrieval succeeds.
- Fallback reasons are empty for the live path or visibly documented if Azure rejects the call.

## References

- [Configure authentication and authorization in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/concepts/authentication-authorization-foundry)
- [Foundry SDK overview](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/sdk-overview)
- [Call chat completion models with Azure OpenAI in Foundry](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/chatgpt)
- [Connect Foundry agents to Foundry IQ knowledge bases](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/foundry-iq-connect)
