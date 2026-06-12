from __future__ import annotations

import json
from contextlib import nullcontext
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable

from pydantic import BaseModel

from ..config import RuntimeConfig


class FoundryClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelJsonResponse:
    raw_json: str
    latency_ms: int
    request_id: str | None = None
    model_deployment: str | None = None
    token_usage: dict[str, int] | None = None
    finish_reason: str | None = None


ProjectClientFactory = Callable[[], Any]


class FoundryModelClient:
    def __init__(
        self,
        config: RuntimeConfig,
        project_client_factory: ProjectClientFactory | None = None,
    ) -> None:
        if not config.foundry_enabled:
            raise FoundryClientError("FoundryModelClient requires effective_mode='foundry'.")
        self.config = config
        self._project_client_factory = project_client_factory or self._build_project_client

    def generate_json(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        user_payload: dict[str, Any],
        output_schema: type[BaseModel],
    ) -> ModelJsonResponse:
        start = perf_counter()
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, indent=2, sort_keys=True),
            },
        ]

        try:
            project_client = self._project_client_factory()
            openai_client = project_client.get_openai_client()
            context_manager = (
                openai_client
                if hasattr(openai_client, "__enter__")
                else nullcontext(openai_client)
            )
            with context_manager as client:
                completion = client.chat.completions.create(
                    model=self.config.azure_ai_model_deployment,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
        except Exception as exc:  # pragma: no cover - exercised with fake clients.
            raise FoundryClientError(f"Foundry model call failed for {agent_name}: {exc}") from exc

        raw_json = self._extract_raw_json(completion)
        latency_ms = max(1, int((perf_counter() - start) * 1000))
        choice = completion.choices[0]

        return ModelJsonResponse(
            raw_json=raw_json,
            latency_ms=latency_ms,
            request_id=getattr(completion, "id", None),
            model_deployment=self.config.azure_ai_model_deployment,
            token_usage=self._extract_usage(completion),
            finish_reason=getattr(choice, "finish_reason", None),
        )

    def _build_project_client(self) -> Any:
        try:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:  # pragma: no cover - depends on optional runtime deps.
            raise FoundryClientError(
                "Install azure-ai-projects and azure-identity to use APP_MODE=foundry."
            ) from exc

        return AIProjectClient(
            endpoint=self.config.azure_ai_project_endpoint,
            credential=DefaultAzureCredential(),
        )

    @staticmethod
    def _extract_raw_json(completion: Any) -> str:
        message = completion.choices[0].message
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()

        parsed = getattr(message, "parsed", None)
        if isinstance(parsed, BaseModel):
            return parsed.model_dump_json()
        if parsed is not None:
            return json.dumps(parsed)

        raise FoundryClientError("Foundry response did not include JSON content.")

    @staticmethod
    def _extract_usage(completion: Any) -> dict[str, int] | None:
        usage = getattr(completion, "usage", None)
        if usage is None:
            return None
        if hasattr(usage, "model_dump"):
            dumped = usage.model_dump()
        elif isinstance(usage, dict):
            dumped = usage
        else:
            return None
        return {
            str(key): int(value)
            for key, value in dumped.items()
            if isinstance(value, int)
        }
