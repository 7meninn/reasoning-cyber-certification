from cybersecurity_readiness.config import load_runtime_config


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


def test_config_falls_back_to_mock_when_foundry_env_is_missing():
    config = load_runtime_config({"APP_MODE": "foundry"})

    assert config.requested_mode == "foundry"
    assert config.effective_mode == "mock"
    assert config.foundry_enabled is False
    assert "AZURE_AI_PROJECT_ENDPOINT" in (config.fallback_reason or "")
    assert "AZURE_AI_MODEL_DEPLOYMENT" in (config.fallback_reason or "")


def test_config_falls_back_to_mock_for_unsupported_mode():
    config = load_runtime_config({"APP_MODE": "surprise"})

    assert config.requested_mode == "mock"
    assert config.effective_mode == "mock"
    assert "Unsupported APP_MODE" in (config.fallback_reason or "")
