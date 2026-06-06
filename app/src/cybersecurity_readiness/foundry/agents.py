from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel

from ..orchestration.state import WorkflowState
from .client import ModelJsonResponse
from .prompts import get_prompt, render_repair_prompt


T = TypeVar("T", bound=BaseModel)


class JsonModelClient(Protocol):
    def generate_json(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        user_payload: dict[str, Any],
        output_schema: type[BaseModel],
    ) -> ModelJsonResponse:
        ...


class FallbackAgent(Protocol[T]):
    name: str
    output_schema: type[T]
    latency_ms: int

    def raw_response(self, context: Any | None = None) -> str:
        ...


def _dump_model(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return None


def build_agent_payload(state: WorkflowState, agent_key: str) -> dict[str, Any]:
    return {
        "agent_key": agent_key,
        "request_text": state.request_text,
        "learner": state.learner.model_dump(mode="json"),
        "input_guardrail": _dump_model(state.input_guardrail),
        "route": _dump_model(state.route),
        "evidence": _dump_model(state.evidence),
        "certification_path": _dump_model(state.certification_path),
        "skill_gap_report": _dump_model(state.skill_gap_report),
        "study_plan": _dump_model(state.study_plan),
        "scenario_lab": _dump_model(state.scenario_lab),
        "assessment_result": _dump_model(state.assessment_result),
        "manager_insight": _dump_model(state.manager_insight),
        "trace_context": {
            "run_id": state.trace.run_id,
            "route": state.trace.route,
            "retrieval_mode": state.trace.retrieval_mode,
            "model_mode": state.trace.model_mode,
        },
        "phase_boundary": {
            "foundry_iq_active": state.trace.retrieval_mode == "foundry_iq",
            "retrieval_mode": state.trace.retrieval_mode,
            "synthetic_data_only": True,
        },
    }


@dataclass
class FoundryBackedAgent(Generic[T]):
    agent_key: str
    fallback_agent: FallbackAgent[T]
    model_client: JsonModelClient
    latency_ms: int = field(init=False)
    last_model_mode: str | None = field(default=None, init=False)
    last_model_deployment: str | None = field(default=None, init=False)
    last_model_request_id: str | None = field(default=None, init=False)
    last_model_token_usage: dict[str, int] | None = field(default=None, init=False)
    last_model_finish_reason: str | None = field(default=None, init=False)
    last_provider_fallback_reason: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.latency_ms = self.fallback_agent.latency_ms

    @property
    def name(self) -> str:
        return self.fallback_agent.name

    @property
    def output_schema(self) -> type[T]:
        return self.fallback_agent.output_schema

    def raw_response(self, context: WorkflowState | None = None) -> str:
        self._reset_metadata()
        if context is None:
            return self._fallback_raw(None, "Missing workflow state for Foundry call.")

        prompt = get_prompt(self.agent_key)
        try:
            response = self.model_client.generate_json(
                agent_name=self.name,
                system_prompt=prompt.render(self.output_schema),
                user_payload=build_agent_payload(context, self.agent_key),
                output_schema=self.output_schema,
            )
        except Exception as exc:
            return self._fallback_raw(context, str(exc))

        self._capture_foundry_response(response)
        return response.raw_json

    def repair_response(
        self,
        raw_json: str,
        exc: Exception,
        state: WorkflowState,
    ) -> str:
        response = self.model_client.generate_json(
            agent_name=f"{self.name} Schema Repair",
            system_prompt=render_repair_prompt(self.name, self.output_schema),
            user_payload={
                "invalid_json": raw_json,
                "validation_error": str(exc),
                "workflow_context": build_agent_payload(state, self.agent_key),
            },
            output_schema=self.output_schema,
        )
        self._capture_foundry_response(response)
        return response.raw_json

    def _fallback_raw(self, context: WorkflowState | None, reason: str) -> str:
        self.last_model_mode = "mock"
        self.last_provider_fallback_reason = f"Foundry fallback: {reason}"
        self.latency_ms = self.fallback_agent.latency_ms
        try:
            return self.fallback_agent.raw_response(context)
        except TypeError:
            return self.fallback_agent.raw_response()

    def _capture_foundry_response(self, response: ModelJsonResponse) -> None:
        self.last_model_mode = "foundry"
        self.last_model_deployment = response.model_deployment
        self.last_model_request_id = response.request_id
        self.last_model_token_usage = response.token_usage
        self.last_model_finish_reason = response.finish_reason
        self.last_provider_fallback_reason = None
        self.latency_ms = response.latency_ms

    def _reset_metadata(self) -> None:
        self.last_model_mode = None
        self.last_model_deployment = None
        self.last_model_request_id = None
        self.last_model_token_usage = None
        self.last_model_finish_reason = None
        self.last_provider_fallback_reason = None
        self.latency_ms = self.fallback_agent.latency_ms
