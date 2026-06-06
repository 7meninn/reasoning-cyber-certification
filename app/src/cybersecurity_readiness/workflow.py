from __future__ import annotations

from .config import RuntimeConfig
from .constants import DEFAULT_DEMO_REQUEST
from .orchestration.runner import OrchestratedWorkflowRunner
from .schemas import LearnerLabResponse, WorkflowResult


def run_demo_workflow(
    learner_id: str = "L-1001",
    request_text: str = DEFAULT_DEMO_REQUEST,
    config: RuntimeConfig | None = None,
    selected_lab_id: str | None = None,
    lab_responses: list[LearnerLabResponse] | None = None,
    demo_response_profile: str = "conditional",
) -> WorkflowResult:
    """Run the SOC readiness workflow with mock or Foundry-backed agents."""
    return OrchestratedWorkflowRunner(config=config).run(
        learner_id=learner_id,
        request_text=request_text,
        selected_lab_id=selected_lab_id,
        lab_responses=lab_responses,
        demo_response_profile=demo_response_profile,
    )
