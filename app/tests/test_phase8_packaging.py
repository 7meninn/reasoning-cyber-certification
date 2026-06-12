import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_env_example_contains_required_live_foundry_variables():
    text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    for name in [
        "APP_MODE",
        "AZURE_AI_PROJECT_ENDPOINT",
        "AZURE_AI_MODEL_DEPLOYMENT",
        "AZURE_AI_SEARCH_ENDPOINT",
        "FOUNDRY_IQ_KNOWLEDGE_BASE",
        "HOSTED_AGENT_API_PORT",
    ]:
        assert name in text

    assert "DefaultAzureCredential" not in text


def test_dockerfile_packages_hosted_api_without_secrets():
    text = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "cybersecurity_readiness.hosted_api" in text
    assert "EXPOSE 8000" in text
    assert "COPY app ./app" in text
    assert "COPY data ./data" in text
    assert "AZURE_AI_PROJECT_ENDPOINT=" not in text
    assert "FOUNDRY_IQ_KNOWLEDGE_BASE=" not in text


def test_phase8_scripts_are_present():
    for script_name in [
        "check_live_foundry.ps1",
        "export_knowledge_docs.ps1",
        "run_hosted_api.ps1",
        "build_hosted_agent_image.ps1",
        "run_hosted_agent_container.ps1",
        "push_acr_image.ps1",
    ]:
        assert (PROJECT_ROOT / "scripts" / script_name).exists()


def test_phase8_docs_cover_live_and_hosted_paths():
    live_doc = (PROJECT_ROOT / "docs" / "live-foundry-setup.md").read_text(encoding="utf-8")
    hosted_doc = (PROJECT_ROOT / "docs" / "hosted-agent-deployment.md").read_text(
        encoding="utf-8"
    )

    assert "APP_MODE=\"foundry_iq\"" in live_doc
    assert "check_live_foundry.ps1 -RequireLive" in live_doc
    assert "Azure Container Registry" in hosted_doc
    assert "POST /invoke" in hosted_doc
    assert "Do not bake secrets into the image" in hosted_doc


def test_foundry_iq_upload_pack_matches_canonical_sources():
    sources = json.loads(
        (PROJECT_ROOT / "data" / "synthetic" / "knowledge_docs" / "sources.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads(
        (
            PROJECT_ROOT
            / "data"
            / "synthetic"
            / "knowledge_docs"
            / "upload"
            / "_manifest.json"
        ).read_text(encoding="utf-8")
    )

    source_ids = {source["source_id"] for source in sources}
    manifest_ids = {entry["source_id"] for entry in manifest}
    assert manifest_ids == source_ids

    for entry in manifest:
        doc_path = PROJECT_ROOT / entry["file"]
        assert doc_path.exists()
        text = doc_path.read_text(encoding="utf-8")
        assert f"Source ID: {entry['source_id']}" in text
        assert "## Safety Boundary" in text
