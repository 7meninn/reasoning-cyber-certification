from cybersecurity_readiness.config import _load_env_file, load_runtime_config


def test_config_defaults_to_mock_mode():
    config = load_runtime_config({})

    assert config.requested_mode == "mock"
    assert config.effective_mode == "mock"
    assert config.foundry_enabled is False
    assert config.fallback_reason is None


def test_config_enables_foundry_when_required_env_is_present():
    config = load_runtime_config(
        {
            "APP_MODE": "foundry",
            "AZURE_AI_PROJECT_ENDPOINT": "https://demo.services.ai.azure.com/api/projects/readiness",
            "AZURE_AI_MODEL_DEPLOYMENT": "gpt-4o-mini",
        }
    )

    assert config.requested_mode == "foundry"
    assert config.effective_mode == "foundry"
    assert config.foundry_enabled is True
    assert config.model_deployment == "gpt-4o-mini"
    assert config.fallback_reason is None


def test_config_enables_foundry_iq_when_required_env_is_present():
    config = load_runtime_config(
        {
            "APP_MODE": "foundry_iq",
            "AZURE_AI_PROJECT_ENDPOINT": "https://demo.services.ai.azure.com/api/projects/readiness",
            "AZURE_AI_MODEL_DEPLOYMENT": "gpt-4o-mini",
            "AZURE_AI_SEARCH_ENDPOINT": "https://demo.search.windows.net",
            "FOUNDRY_IQ_KNOWLEDGE_BASE": "soc-readiness-kb",
            "FOUNDRY_IQ_MAX_DOCS": "5",
            "FOUNDRY_IQ_MAX_OUTPUT_TOKENS": "2048",
        }
    )

    assert config.requested_mode == "foundry_iq"
    assert config.effective_mode == "foundry_iq"
    assert config.foundry_enabled is True
    assert config.foundry_iq_enabled is True
    assert config.model_mode == "foundry"
    assert config.retrieval_mode == "foundry_iq"
    assert config.foundry_iq_knowledge_base == "soc-readiness-kb"
    assert config.foundry_iq_max_docs == 5
    assert config.foundry_iq_max_output_tokens == 2048


def test_config_falls_back_to_mock_when_foundry_env_is_missing():
    config = load_runtime_config({"APP_MODE": "foundry"})

    assert config.requested_mode == "foundry"
    assert config.effective_mode == "mock"
    assert config.foundry_enabled is False
    assert "AZURE_AI_PROJECT_ENDPOINT" in (config.fallback_reason or "")
    assert "AZURE_AI_MODEL_DEPLOYMENT" in (config.fallback_reason or "")


def test_config_falls_back_to_mock_when_foundry_iq_env_is_missing():
    config = load_runtime_config(
        {
            "APP_MODE": "foundry_iq",
            "AZURE_AI_PROJECT_ENDPOINT": "https://demo.services.ai.azure.com/api/projects/readiness",
            "AZURE_AI_MODEL_DEPLOYMENT": "gpt-4o-mini",
        }
    )

    assert config.requested_mode == "foundry_iq"
    assert config.effective_mode == "mock"
    assert config.foundry_iq_enabled is False
    assert "AZURE_AI_SEARCH_ENDPOINT" in (config.fallback_reason or "")
    assert "FOUNDRY_IQ_KNOWLEDGE_BASE" in (config.fallback_reason or "")


def test_config_falls_back_to_mock_for_unsupported_mode():
    config = load_runtime_config({"APP_MODE": "surprise"})

    assert config.requested_mode == "mock"
    assert config.effective_mode == "mock"
    assert "Unsupported APP_MODE" in (config.fallback_reason or "")


def test_config_reads_dotenv_style_files(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "# local only",
                'APP_MODE="foundry"',
                "AZURE_AI_PROJECT_ENDPOINT=https://demo.services.ai.azure.com/api/projects/readiness",
                "AZURE_AI_MODEL_DEPLOYMENT=gpt-5.2",
            ]
        ),
        encoding="utf-8",
    )

    env = _load_env_file(dotenv)
    config = load_runtime_config(env)

    assert config.requested_mode == "foundry"
    assert config.effective_mode == "foundry"
    assert config.model_deployment == "gpt-5.2"


def test_config_treats_placeholder_values_as_missing():
    config = load_runtime_config(
        {
            "APP_MODE": "foundry",
            "AZURE_AI_PROJECT_ENDPOINT": "https://<resource>.services.ai.azure.com/api/projects/<project>",
            "AZURE_AI_MODEL_DEPLOYMENT": "<deployment-name>",
        }
    )

    assert config.requested_mode == "foundry"
    assert config.effective_mode == "mock"
    assert "AZURE_AI_PROJECT_ENDPOINT" in (config.fallback_reason or "")
    assert "AZURE_AI_MODEL_DEPLOYMENT" in (config.fallback_reason or "")
