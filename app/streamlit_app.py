from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cybersecurity_readiness.config import RuntimeConfig, load_runtime_config  # noqa: E402
from cybersecurity_readiness.loader import load_learners  # noqa: E402
from cybersecurity_readiness.schemas import Citation, WorkflowResult  # noqa: E402
from cybersecurity_readiness.workflow import DEFAULT_DEMO_REQUEST, run_demo_workflow  # noqa: E402


st.set_page_config(
    page_title="SOC Readiness Command Center",
    page_icon=None,
    layout="wide",
)


def render_citations(citations: list[Citation]) -> None:
    for citation in citations:
        label = f"{citation.source_id}: {citation.title}"
        if citation.url:
            st.markdown(f"- [{label}]({citation.url})")
        else:
            st.markdown(f"- {label}")


def get_or_run_demo(
    learner_id: str,
    request_text: str,
    config: RuntimeConfig,
) -> WorkflowResult:
    cached = st.session_state.get("workflow_result")
    cached_learner = st.session_state.get("workflow_learner_id")
    cached_request = st.session_state.get("workflow_request_text")
    cached_mode = st.session_state.get("workflow_mode_label")
    if (
        cached
        and cached_learner == learner_id
        and cached_request == request_text
        and cached_mode == config.mode_label
    ):
        return cached

    result = run_demo_workflow(
        learner_id=learner_id,
        request_text=request_text,
        config=config,
    )
    st.session_state["workflow_result"] = result
    st.session_state["workflow_learner_id"] = learner_id
    st.session_state["workflow_request_text"] = request_text
    st.session_state["workflow_mode_label"] = config.mode_label
    return result


runtime_config = load_runtime_config()
learners = load_learners()
learner_ids = [learner.learner_id for learner in learners]

with st.sidebar:
    st.header("Demo Controls")
    if st.button("Reset Demo", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    selected_learner = st.selectbox("Synthetic learner", options=learner_ids, index=0)
    request_text = st.text_area("Demo request", value=DEFAULT_DEMO_REQUEST, height=150)
    run_clicked = st.button("Run Demo", type="primary", use_container_width=True)
    st.divider()
    st.caption(f"Requested mode: {runtime_config.requested_mode}")
    st.caption(f"Execution mode: {runtime_config.effective_mode}")
    st.caption(f"Retrieval: {runtime_config.retrieval_mode}")
    if runtime_config.model_deployment:
        st.caption(f"Model deployment: {runtime_config.model_deployment}")
    if runtime_config.foundry_iq_knowledge_base:
        st.caption(f"Knowledge base: {runtime_config.foundry_iq_knowledge_base}")
    if runtime_config.fallback_reason:
        st.warning(runtime_config.fallback_reason)
    elif runtime_config.foundry_iq_enabled:
        st.success("Foundry IQ retrieval enabled")
    elif runtime_config.foundry_enabled:
        st.success("Foundry model calls enabled")
    else:
        st.caption("Cloud credentials: not required")

if run_clicked or "workflow_result" not in st.session_state:
    try:
        result = get_or_run_demo(selected_learner, request_text, runtime_config)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
else:
    result = get_or_run_demo(selected_learner, request_text, runtime_config)

learner = result.learner
trace = result.trace

st.title("SOC Readiness Command Center")
st.caption(
    "Phase 4 multi-agent SOC readiness demo. Mock mode is deterministic; Foundry mode "
    "uses model-backed JSON agents. Foundry IQ mode adds live knowledge-base retrieval "
    "with explicit local fallback. All data, users, teams, logs, and incidents are synthetic."
)

if result.safety_response is not None:
    st.error(result.safety_response.message)
    st.subheader("Safe Alternatives")
    for alternative in result.safety_response.safe_alternatives:
        st.write(f"- {alternative}")
    with st.expander("Agent Trace", expanded=True):
        st.json(trace.model_dump(mode="json"))
    st.stop()

if result.route.route == "manager_insights":
    manager = result.manager_insight
    if manager is None:
        st.error("Manager route did not return manager insight.")
        st.stop()
    summary_cols = st.columns(4)
    summary_cols[0].metric("Route", "Manager")
    summary_cols[1].metric("Team", manager.team_id)
    summary_cols[2].metric("Capacity risk", manager.capacity_risk)
    summary_cols[3].metric("Trace latency", f"{trace.latency_ms} ms")
    st.subheader("Manager Dashboard")
    st.write(manager.summary)
    st.dataframe(
        [{"Verdict": key, "Learners": value} for key, value in manager.readiness_distribution.items()],
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Top Skill Gaps")
    for gap in manager.top_skill_gaps:
        st.write(f"- {gap}")
    st.subheader("Recommended Actions")
    for action in manager.recommended_actions:
        st.write(f"- {action}")
    st.caption(manager.privacy_note)
    with st.expander("Agent Trace", expanded=False):
        st.json(trace.model_dump(mode="json"))
    st.stop()

if (
    result.certification_path is None
    or result.skill_gap_report is None
    or result.study_plan is None
    or result.scenario_lab is None
    or result.assessment_result is None
    or result.manager_insight is None
):
    st.error("Workflow did not return the complete learner demo path.")
    with st.expander("Agent Trace", expanded=True):
        st.json(trace.model_dump(mode="json"))
    st.stop()

path = result.certification_path
gaps = result.skill_gap_report
plan = result.study_plan
lab = result.scenario_lab
assessment = result.assessment_result
manager = result.manager_insight

summary_cols = st.columns(4)
summary_cols[0].metric("Learner", learner.learner_id)
summary_cols[1].metric("Target", learner.role_target)
summary_cols[2].metric("Readiness", assessment.overall_readiness)
summary_cols[3].metric("Trace latency", f"{trace.latency_ms} ms")
st.caption(
    f"Mode: {trace.requested_app_mode} -> {trace.effective_app_mode}; "
    f"model: {trace.model_mode}; retrieval: {trace.retrieval_mode}; "
    f"citations: {len(trace.citations)}"
)
if trace.mode_fallback_reason:
    st.warning(trace.mode_fallback_reason)
if trace.retrieval_fallback_reason:
    st.warning(f"Retrieval fallback: {trace.retrieval_fallback_reason}")

tabs = st.tabs(["Learner", "Path", "Skill Gaps", "Study Plan", "Scenario Lab", "Assessment", "Manager"])

with tabs[0]:
    st.subheader("Learner Profile")
    st.dataframe(
        [
            {"Field": "Current role", "Value": learner.role_current},
            {"Field": "Target role", "Value": learner.role_target},
            {"Field": "Experience", "Value": learner.experience_level},
            {"Field": "Focus hours", "Value": learner.available_focus_hours_per_week},
            {"Field": "Learning style", "Value": learner.preferred_learning_style},
            {"Field": "Completed certifications", "Value": ", ".join(learner.completed_certifications) or "None"},
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Self-Rated Skills")
    skill_cols = st.columns(3)
    for index, (skill, score) in enumerate(learner.skills_self_rating.items()):
        with skill_cols[index % 3]:
            st.metric(skill.replace("_", " ").title(), f"{score}/5")
    st.subheader("Constraints")
    for constraint in learner.constraints:
        st.write(f"- {constraint}")

with tabs[1]:
    st.subheader("Certification Path")
    st.write(path.rationale)
    st.markdown("**Recommended certifications**")
    for item in path.recommended_certifications:
        st.write(f"- {item}")
    st.markdown("**Sequence**")
    for index, step in enumerate(path.sequence, start=1):
        st.write(f"{index}. {step}")
    st.markdown("**Caveats**")
    for caveat in path.caveats:
        st.warning(caveat)
    st.markdown("**Citations**")
    render_citations(path.citations)

with tabs[2]:
    st.subheader("Skill Gap Heatmap")
    rows = []
    for domain in gaps.domain_scores:
        rows.append(
            {
                "Domain": domain.domain,
                "Current": domain.current_score,
                "Target": domain.target_score,
                "Gap": domain.target_score - domain.current_score,
                "Priority": domain.priority,
                "Evidence": domain.evidence,
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.subheader("Priority Focus")
    for focus in gaps.recommended_focus:
        st.write(f"- {focus}")

with tabs[3]:
    st.subheader("4-Week Study Plan")
    fit_cols = st.columns(3)
    fit_cols[0].metric("Available focus hours", plan.workload_fit.available_focus_hours_per_week)
    fit_cols[1].metric("Planned hours", plan.workload_fit.planned_hours_per_week)
    fit_cols[2].metric("Workload fit", plan.workload_fit.fit.title())
    st.write(plan.workload_fit.rationale)
    for week in plan.weekly_modules:
        with st.expander(f"Week {week.week}: {week.theme}", expanded=week.week == 1):
            st.metric("Total hours", week.total_hours)
            st.write(f"Scenario lab: {week.scenario_lab}")
            st.write(f"Checkpoint: {week.checkpoint}")
            st.dataframe(
                [
                    {
                        "Day": task.day,
                        "Task": task.title,
                        "Minutes": task.duration_minutes,
                        "Type": task.activity_type,
                        "Outcome": task.outcome,
                    }
                    for task in week.tasks
                ],
                hide_index=True,
                use_container_width=True,
            )

with tabs[4]:
    st.subheader(lab.title)
    st.write(lab.prompt)
    for artifact in lab.artifacts:
        with st.expander(f"{artifact.artifact_type}: {artifact.name}", expanded=True):
            st.code(artifact.content)
    st.markdown("**Learner task**")
    st.write(lab.learner_task)
    st.markdown("**Expected investigation path**")
    for step in lab.expected_investigation_path:
        st.write(f"- {step}")
    st.markdown("**Rubric**")
    st.dataframe(
        [
            {
                "Criterion": item.criterion,
                "Points": item.max_points,
                "Expected signal": item.expected_signal,
            }
            for item in lab.rubric
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.caption(lab.safety_note)

with tabs[5]:
    st.subheader("Assessment Result")
    assess_cols = st.columns(3)
    assess_cols[0].metric("Verdict", assessment.overall_readiness)
    assess_cols[1].metric("Overall score", assessment.overall_score)
    assess_cols[2].metric("Confidence", f"{assessment.confidence:.0%}")
    st.write(assessment.recommendation)
    st.subheader("Domain Scores")
    st.dataframe(
        [{"Domain": domain, "Score": score} for domain, score in assessment.domain_scores.items()],
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Evidence")
    for item in assessment.evidence:
        st.write(f"- {item}")
    st.subheader("Remediation Sprint")
    st.dataframe(
        [
            {
                "Task": task.title,
                "Focus": task.focus_domain,
                "Minutes": task.duration_minutes,
                "Outcome": task.outcome,
            }
            for task in assessment.remediation_plan.tasks
        ],
        hide_index=True,
        use_container_width=True,
    )

with tabs[6]:
    st.subheader("Manager Dashboard")
    st.write(manager.summary)
    dist_cols = st.columns(3)
    dist_cols[0].metric("GO", manager.readiness_distribution.get("GO", 0))
    dist_cols[1].metric("CONDITIONAL", manager.readiness_distribution.get("CONDITIONAL", 0))
    dist_cols[2].metric("NOT YET", manager.readiness_distribution.get("NOT_YET", 0))
    st.metric("Capacity risk", manager.capacity_risk)
    st.subheader("Top Skill Gaps")
    for gap in manager.top_skill_gaps:
        st.write(f"- {gap}")
    st.subheader("Recommended Actions")
    for action in manager.recommended_actions:
        st.write(f"- {action}")
    st.caption(manager.privacy_note)

with st.expander("Agent Trace", expanded=False):
    st.json(trace.model_dump(mode="json"))
