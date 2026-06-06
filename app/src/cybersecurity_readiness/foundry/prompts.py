from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


BASE_GUARDRAILS = """
You are part of a multi-agent SOC Analyst certification-readiness demo.
Return only JSON that matches the supplied Pydantic schema. Do not wrap JSON in Markdown.
Use only synthetic learner, team, work-signal, and lab data from the payload.
Keep all cybersecurity content defensive, educational, and authorization-bound.
Never provide exam dumps, real exam questions, credential material, secrets, or real PII.
Never guarantee that a learner will pass a certification exam.
Preserve citations from the provided local evidence when the schema supports citations.
Keep retrieval_mode honest as local_mock; Foundry IQ is not active in this phase.
""".strip()


@dataclass(frozen=True)
class AgentPrompt:
    role: str
    task: str

    def render(self, schema: type[BaseModel]) -> str:
        return "\n\n".join(
            [
                BASE_GUARDRAILS,
                f"Agent role: {self.role}",
                f"Task: {self.task}",
                f"Output schema name: {schema.__name__}",
            ]
        )


PROMPTS: dict[str, AgentPrompt] = {
    "certification_path_advisor": AgentPrompt(
        role="Certification Path Advisor Agent",
        task=(
            "Recommend the SOC Analyst readiness certification path for the learner. "
            "Anchor the MVP path on Security+ foundation plus SC-200-oriented SOC readiness."
        ),
    ),
    "skill_gap_analyst": AgentPrompt(
        role="Skill Gap Analyst Agent",
        task=(
            "Compare the learner profile, evidence bundle, and target path to produce "
            "domain-level readiness gaps and priority focus areas."
        ),
    ),
    "study_plan_generator": AgentPrompt(
        role="Study Plan Generator Agent",
        task=(
            "Generate a 4-week study plan that respects the learner's available focus "
            "hours and includes scenario-based checkpoints."
        ),
    ),
    "assessment": AgentPrompt(
        role="Assessment Agent",
        task=(
            "Assess the synthetic lab performance and return a GO, CONDITIONAL, or "
            "NOT_YET readiness result with a remediation sprint."
        ),
    ),
    "manager_insights": AgentPrompt(
        role="Manager Insights Agent",
        task=(
            "Produce aggregate manager-safe team readiness insight without exposing "
            "private learner weaknesses."
        ),
    ),
}


def get_prompt(agent_key: str) -> AgentPrompt:
    try:
        return PROMPTS[agent_key]
    except KeyError as exc:
        raise ValueError(f"No Foundry prompt registered for {agent_key}.") from exc


def render_repair_prompt(agent_name: str, schema: type[BaseModel]) -> str:
    return "\n\n".join(
        [
            BASE_GUARDRAILS,
            f"Agent role: Schema Repair for {agent_name}",
            (
                "Repair the invalid JSON from the previous model response. "
                "Preserve the intent and citations when possible, but return only "
                f"valid JSON for schema {schema.__name__}."
            ),
        ]
    )
