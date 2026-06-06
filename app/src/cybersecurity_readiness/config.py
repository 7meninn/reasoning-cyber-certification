from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Literal, Mapping


AppMode = Literal["mock", "foundry"]

DEFAULT_AZURE_OPENAI_API_VERSION = "2024-10-21"
VALID_APP_MODES: tuple[AppMode, ...] = ("mock", "foundry")


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
    fallback_reason: str | None = None

    @property
    def foundry_enabled(self) -> bool:
        return self.effective_mode == "foundry"

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

    effective_mode: AppMode = requested_mode
    if requested_mode == "foundry":
        missing = []
        if endpoint is None:
            missing.append("AZURE_AI_PROJECT_ENDPOINT")
        if deployment is None:
            missing.append("AZURE_AI_MODEL_DEPLOYMENT")
        if missing:
            effective_mode = "mock"
            fallback_reason = (
                "APP_MODE=foundry requires "
                f"{', '.join(missing)}; using deterministic mock mode."
            )

    return RuntimeConfig(
        requested_mode=requested_mode,
        effective_mode=effective_mode,
        azure_ai_project_endpoint=endpoint,
        azure_ai_model_deployment=deployment,
        azure_openai_api_version=api_version,
        fallback_reason=fallback_reason,
    )
