from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Literal, Mapping


AppMode = Literal["mock", "foundry", "foundry_iq"]
ModelMode = Literal["mock", "foundry"]
RetrievalMode = Literal["local_mock", "foundry_iq"]

DEFAULT_AZURE_OPENAI_API_VERSION = "2024-10-21"
DEFAULT_FOUNDRY_IQ_API_VERSION = "2026-05-01-preview"
DEFAULT_FOUNDRY_IQ_MAX_DOCS = 8
DEFAULT_FOUNDRY_IQ_MAX_OUTPUT_TOKENS = 4096
VALID_APP_MODES: tuple[AppMode, ...] = ("mock", "foundry", "foundry_iq")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


@dataclass(frozen=True)
class RuntimeConfig:
    requested_mode: AppMode
    effective_mode: AppMode
    azure_ai_project_endpoint: str | None = None
    azure_ai_model_deployment: str | None = None
    azure_openai_api_version: str = DEFAULT_AZURE_OPENAI_API_VERSION
    azure_ai_search_endpoint: str | None = None
    foundry_iq_knowledge_base: str | None = None
    foundry_iq_api_version: str = DEFAULT_FOUNDRY_IQ_API_VERSION
    foundry_iq_max_docs: int = DEFAULT_FOUNDRY_IQ_MAX_DOCS
    foundry_iq_max_output_tokens: int = DEFAULT_FOUNDRY_IQ_MAX_OUTPUT_TOKENS
    fallback_reason: str | None = None

    @property
    def foundry_enabled(self) -> bool:
        return self.effective_mode in ("foundry", "foundry_iq")

    @property
    def foundry_iq_enabled(self) -> bool:
        return self.effective_mode == "foundry_iq"

    @property
    def model_mode(self) -> ModelMode:
        return "foundry" if self.foundry_enabled else "mock"

    @property
    def retrieval_mode(self) -> RetrievalMode:
        return "foundry_iq" if self.foundry_iq_enabled else "local_mock"

    @property
    def model_deployment(self) -> str | None:
        return self.azure_ai_model_deployment

    @property
    def mode_label(self) -> str:
        if self.requested_mode == self.effective_mode:
            return self.effective_mode
        return f"{self.requested_mode} -> {self.effective_mode}"


def load_runtime_config(env: Mapping[str, str] | None = None) -> RuntimeConfig:
    source = environ if env is None else env
    raw_mode = _clean(source.get("APP_MODE")) or "mock"
    normalized_mode = raw_mode.lower()
    fallback_reason: str | None = None

    if normalized_mode not in VALID_APP_MODES:
        requested_mode: AppMode = "mock"
        fallback_reason = f"Unsupported APP_MODE={raw_mode!r}; using mock mode."
    else:
        requested_mode = normalized_mode  # type: ignore[assignment]

    endpoint = _clean(source.get("AZURE_AI_PROJECT_ENDPOINT"))
    deployment = _clean(source.get("AZURE_AI_MODEL_DEPLOYMENT"))
    api_version = _clean(source.get("AZURE_OPENAI_API_VERSION")) or DEFAULT_AZURE_OPENAI_API_VERSION
    search_endpoint = _clean(source.get("AZURE_AI_SEARCH_ENDPOINT"))
    knowledge_base = _clean(source.get("FOUNDRY_IQ_KNOWLEDGE_BASE"))
    iq_api_version = _clean(source.get("FOUNDRY_IQ_API_VERSION")) or DEFAULT_FOUNDRY_IQ_API_VERSION
    iq_max_docs = _clean_int(source.get("FOUNDRY_IQ_MAX_DOCS"), DEFAULT_FOUNDRY_IQ_MAX_DOCS)
    iq_max_output_tokens = _clean_int(
        source.get("FOUNDRY_IQ_MAX_OUTPUT_TOKENS"),
        DEFAULT_FOUNDRY_IQ_MAX_OUTPUT_TOKENS,
    )

    effective_mode: AppMode = requested_mode
    if requested_mode in ("foundry", "foundry_iq"):
        missing = []
        if endpoint is None:
            missing.append("AZURE_AI_PROJECT_ENDPOINT")
        if deployment is None:
            missing.append("AZURE_AI_MODEL_DEPLOYMENT")
        if requested_mode == "foundry_iq":
            if search_endpoint is None:
                missing.append("AZURE_AI_SEARCH_ENDPOINT")
            if knowledge_base is None:
                missing.append("FOUNDRY_IQ_KNOWLEDGE_BASE")
        if missing:
            effective_mode = "mock"
            fallback_reason = (
                f"APP_MODE={requested_mode} requires "
                f"{', '.join(missing)}; using deterministic mock mode."
            )

    return RuntimeConfig(
        requested_mode=requested_mode,
        effective_mode=effective_mode,
        azure_ai_project_endpoint=endpoint,
        azure_ai_model_deployment=deployment,
        azure_openai_api_version=api_version,
        azure_ai_search_endpoint=search_endpoint,
        foundry_iq_knowledge_base=knowledge_base,
        foundry_iq_api_version=iq_api_version,
        foundry_iq_max_docs=iq_max_docs,
        foundry_iq_max_output_tokens=iq_max_output_tokens,
        fallback_reason=fallback_reason,
    )


def _clean_int(value: str | None, default: int) -> int:
    cleaned = _clean(value)
    if cleaned is None:
        return default
    try:
        parsed = int(cleaned)
    except ValueError:
        return default
    return max(1, parsed)
