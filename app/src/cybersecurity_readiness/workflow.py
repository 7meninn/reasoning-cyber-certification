from __future__ import annotations

from .constants import DEFAULT_DEMO_REQUEST
from .orchestration.runner import OrchestratedWorkflowRunner
from .schemas import WorkflowResult


def run_demo_workflow(
    learner_id: str = "L-1001",
    request_text: str = DEFAULT_DEMO_REQUEST,
) -> WorkflowResult:
    """Run the deterministic local workflow through the Phase 2 orchestrator."""
    return OrchestratedWorkflowRunner().run(
        learner_id=learner_id,
        request_text=request_text,
    )

