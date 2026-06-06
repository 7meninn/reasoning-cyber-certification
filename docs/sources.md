# Sources and Foundry IQ Setup

Phase 4 keeps all grounding data synthetic or public-summary only. The canonical local source list is:

```text
data/synthetic/knowledge_docs/sources.json
```

## Source Types

- `official_public_summary`: short public summaries and links for certification pages such as Microsoft SC-200 and CompTIA Security+.
- `synthetic_internal`: demo-only SOC readiness guidance, triage playbooks, and learner enablement notes.
- `synthetic_policy`: demo-only manager, privacy, and work-capacity guidance.
- `synthetic_lab`: demo-only lab artifacts and safety notes.

## Foundry IQ Knowledge Base

Use the JSON source list to create or seed a Foundry IQ-compatible Azure AI Search knowledge base. Each source should preserve:

- `source_id`
- `title`
- `source_type`
- `url`
- `summary`
- `excerpt`
- `tags`
- `metadata`

Recommended semantic content fields are `title`, `summary`, `excerpt`, and `tags`. Keep `source_id` retrievable because the app uses it for citation validation.

## Runtime Configuration

```powershell
$env:APP_MODE="foundry_iq"
$env:AZURE_AI_PROJECT_ENDPOINT="https://<resource>.services.ai.azure.com/api/projects/<project>"
$env:AZURE_AI_MODEL_DEPLOYMENT="<deployment-name>"
$env:AZURE_AI_SEARCH_ENDPOINT="https://<search-service>.search.windows.net"
$env:FOUNDRY_IQ_KNOWLEDGE_BASE="<knowledge-base-name>"
```

The retrieval adapter calls the knowledge base retrieve API with Microsoft Entra ID credentials. If the live call fails, returns malformed data, or returns no citations, the app falls back to `local_mock` and records the reason in `RunTrace`.

## Safety Boundary

Do not add real employee records, tenant logs, customer incidents, credentials, secrets, or real exam questions to the knowledge base. The demo is designed to stay synthetic and defensive.
