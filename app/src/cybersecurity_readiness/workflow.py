from __future__ import annotations

from .config import RuntimeConfig
from .constants import DEFAULT_DEMO_REQUEST
from .orchestration.runner import OrchestratedWorkflowRunner
from .schemas import WorkflowResult


def run_demo_workflow(
    learner_id: str = "L-1001",
    request_text: str = DEFAULT_DEMO_REQUEST,
    config: RuntimeConfig | None = None,
) -> WorkflowResult:
    """Run the SOC readiness workflow with mock or Foundry-backed agents."""
    return OrchestratedWorkflowRunner(config=config).run(
        learner_id=learner_id,
        request_text=request_text,
    )
