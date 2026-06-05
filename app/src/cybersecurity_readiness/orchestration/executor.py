from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from ..agents import AgentResult, parse_agent_json
from ..schemas import AgentStep, GuardrailVerdict, RunTrace
from .fallbacks import fallback_for_schema, fallback_guardrail
from .state import WorkflowState


T = TypeVar("T", bound=BaseModel)


class RawJsonAgent(Protocol[T]):
    name: str
    output_schema: type[T]
    latency_ms: int

    def raw_response(self, context: Any | None = None) -> str:
        ...


RepairJson = Callable[[str, Exception, WorkflowState], str]
FallbackFactory = Callable[[type[T], str], T]


@dataclass
class AgentExecutor(Generic[T]):
    agent: RawJsonAgent[T]
    repair_json: RepairJson | None = None
    fallback_factory: FallbackFactory[T] | None = None

    @property
    def name(self) -> str:
        return self.agent.name

    @property
    def output_schema(self) -> type[T]:
        return self.agent.output_schema

    def execute(self, state: WorkflowState, input_summary: str) -> AgentResult[T]:
        raw_json = self._raw_response(state)
        parsed: T
        status = "success"
        attempt_count = 1
        repair_attempted = False
        fallback_used = False
        validation_error: str | None = None
        repair_notes: str | None = None

        try:
            parsed = parse_agent_json(raw_json, self.output_schema)
        except (TypeError, ValueError, ValidationError) as exc:
            validation_error = str(exc)
            repair_attempted = True
            repair_verdict = fallback_guardrail(f"{self.name} invalid schema")
            state.trace.guardrail_verdicts.append(repair_verdict)

            if self.repair_json is not None:
                attempt_count = 2
                repair_notes = "schema repair attempted"
                try:
                    repaired_json = self.repair_json(raw_json, exc, state)
                    parsed = parse_agent_json(repaired_json, self.output_schema)
                    raw_json = repaired_json
                    status = "repaired"
                except (TypeError, ValueError, ValidationError) as repair_exc:
                    validation_error = f"{validation_error}\nRepair failed: {repair_exc}"
                    parsed = self._fallback(state, validation_error)
                    fallback_used = True
                    status = "fallback"
            else:
                parsed = self._fallback(state, validation_error)
                fallback_used = True
                status = "fallback"

        self._record_step(
            trace=state.trace,
            input_summary=input_summary,
            raw_json=raw_json,
            parsed=parsed,
            status=status,
            attempt_count=attempt_count,
            repair_attempted=repair_attempted,
            fallback_used=fallback_used,
            validation_error=validation_error,
            repair_notes=repair_notes,
        )
        if fallback_used:
            state.fallback_flags.append(self.name)
        return AgentResult(raw_json=raw_json, parsed=parsed)

    def _raw_response(self, state: WorkflowState) -> str:
        try:
            return self.agent.raw_response(state)
        except TypeError:
            return self.agent.raw_response()

    def _fallback(self, state: WorkflowState, reason: str) -> T:
        factory = self.fallback_factory or fallback_for_schema
        fallback = factory(self.output_schema, reason)
        state.errors.append(f"{self.name}: {reason}")
        return fallback

    def _record_step(
        self,
        trace: RunTrace,
        input_summary: str,
        raw_json: str,
        parsed: T,
        status: str,
        attempt_count: int,
        repair_attempted: bool,
        fallback_used: bool,
        validation_error: str | None,
        repair_notes: str | None,
    ) -> None:
        citations = list(getattr(parsed, "citations", []))
        guardrails = [parsed] if isinstance(parsed, GuardrailVerdict) else []
        if hasattr(parsed, "guardrail_verdict"):
            guardrails.append(getattr(parsed, "guardrail_verdict"))
        retrieval_mode = getattr(parsed, "retrieval_mode", None)

        trace.agent_steps.append(
            AgentStep(
                agent_name=self.name,
                latency_ms=self.agent.latency_ms,
                input_summary=input_summary,
                raw_json_response=raw_json,
                parsed_output=parsed.model_dump(mode="json"),
                citations=citations,
                guardrail_verdicts=guardrails,
                retrieval_mode=retrieval_mode,
                status=status,  # type: ignore[arg-type]
                attempt_count=attempt_count,
                repair_attempted=repair_attempted,
                fallback_used=fallback_used,
                validation_error=validation_error,
                repair_notes=repair_notes,
            )
        )
        trace.latency_ms += self.agent.latency_ms
        trace.citations.extend(citations)
        trace.guardrail_verdicts.extend(guardrails)

