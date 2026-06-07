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
