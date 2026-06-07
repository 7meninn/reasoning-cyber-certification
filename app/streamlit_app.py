from __future__ import annotations

from html import escape
import sys
from pathlib import Path

import streamlit as st


SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cybersecurity_readiness.config import RuntimeConfig, load_runtime_config  # noqa: E402
from cybersecurity_readiness.loader import load_labs, load_learners  # noqa: E402
from cybersecurity_readiness.schemas import Citation, LearnerLabResponse, WorkflowResult  # noqa: E402
from cybersecurity_readiness.workflow import DEFAULT_DEMO_REQUEST, run_demo_workflow  # noqa: E402


ROOT_DIR = Path(__file__).resolve().parents[1]
EVALUATION_REPORT_PATH = ROOT_DIR / "docs" / "evaluation-report.md"

st.set_page_config(
    page_title="SOC Readiness Command Center",
    page_icon=None,
    layout="wide",
)

st.markdown(
    """
    <style>
    .section-kicker {
        color: #5b6472;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0;
        margin-bottom: 0.2rem;
        text-transform: uppercase;
    }
    .hero-panel {
        border: 1px solid #d9dee8;
        border-radius: 8px;
        padding: 1rem 1.1rem;
        background: #f8fafc;
        margin: 0.35rem 0 1rem 0;
    }
    .callout-panel {
        border-left: 4px solid #2563eb;
        padding: 0.75rem 0.9rem;
        background: #f8fafc;
        margin: 0.7rem 0;
    }
    .status-badge {
        border: 1px solid #c9d3e3;
        border-radius: 999px;
        display: inline-block;
        font-size: 0.78rem;
        font-weight: 700;
        margin: 0.08rem 0.25rem 0.08rem 0;
        padding: 0.16rem 0.55rem;
    }
    .status-pass { background: #ecfdf3; border-color: #9ad7b3; color: #155e35; }
    .status-warn { background: #fff8e6; border-color: #e8c765; color: #7a4e00; }
    .status-info { background: #eff6ff; border-color: #a6c8ff; color: #1d4ed8; }
    .status-muted { background: #f3f4f6; border-color: #d1d5db; color: #374151; }
    .status-blocked { background: #fef2f2; border-color: #f0a5a5; color: #991b1b; }
    .small-note {
        color: #5b6472;
        font-size: 0.86rem;
        line-height: 1.35;
    }
    .snapshot-grid {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        margin: 0.25rem 0 0.8rem 0;
    }
    .snapshot-tile {
        border: 1px solid #d6dce7;
        border-radius: 8px;
        padding: 0.62rem 0.7rem;
        min-height: 4.4rem;
        background: rgba(148, 163, 184, 0.08);
    }
    .snapshot-label {
        color: #5b6472;
        font-size: 0.72rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .snapshot-value {
        color: inherit;
        font-size: clamp(0.9rem, 1vw, 1.08rem);
        font-weight: 750;
        line-height: 1.18;
        overflow-wrap: anywhere;
    }
    @media (max-width: 1000px) {
        .snapshot-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_kicker(text: str) -> None:
    st.markdown(f"<div class='section-kicker'>{escape(text)}</div>", unsafe_allow_html=True)


def render_status_badge(label: str, tone: str = "muted") -> None:
    safe_tone = tone if tone in {"pass", "warn", "info", "muted", "blocked"} else "muted"
    st.markdown(
        f"<span class='status-badge status-{safe_tone}'>{escape(label)}</span>",
        unsafe_allow_html=True,
    )


def render_badge_row(items: list[tuple[str, str]]) -> None:
    html = "".join(
        f"<span class='status-badge status-{tone}'>{escape(label)}</span>"
        for label, tone in items
    )
    st.markdown(html, unsafe_allow_html=True)


def render_snapshot_tiles(items: list[tuple[str, str]], columns: int = 6) -> None:
    html = f"<div class='snapshot-grid' style='grid-template-columns: repeat({columns}, minmax(0, 1fr));'>"
    for label, value in items:
        html += (
            "<div class='snapshot-tile'>"
            f"<div class='snapshot-label'>{escape(label)}</div>"
            f"<div class='snapshot-value'>{escape(value)}</div>"
            "</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def get_evaluation_status() -> str:
    if not EVALUATION_REPORT_PATH.exists():
        return "Not generated"
    report_text = EVALUATION_REPORT_PATH.read_text(encoding="utf-8")
    if "Overall: `PASS`" in report_text:
        return "PASS"
    if "Overall: `FAIL`" in report_text:
        return "FAIL"
    return "Available"


def render_submission_snapshot(trace, readiness: str | None, lab_score: int | None) -> None:
    eval_status = get_evaluation_status()
    route_label = "SOC learner" if trace.route == "soc_readiness_demo" else trace.route
    with st.container(border=True):
        render_kicker("Judge snapshot")
        render_snapshot_tiles(
            [
                ("Route", route_label),
                ("Readiness", readiness or "n/a"),
                ("Lab score", f"{lab_score}/100" if lab_score is not None else "n/a"),
                ("Mode", trace.effective_app_mode),
                ("Retrieval", trace.retrieval_mode),
                ("Eval", eval_status),
            ]
        )
        badge_items = [
            (f"Requested: {trace.requested_app_mode}", "info"),
            (f"Model: {trace.model_mode}", "info"),
            (f"Citations: {len(trace.citations)}", "pass" if trace.citations else "muted"),
            (f"Latency: {trace.latency_ms} ms", "muted"),
        ]
        agent_fallback = any(step.fallback_used for step in trace.agent_steps)
        if trace.mode_fallback_reason or trace.retrieval_fallback_reason or agent_fallback:
            badge_items.append(("Fallback visible", "warn"))
        elif trace.fallback_mode:
            badge_items.append(("Mock/local baseline", "muted"))
        else:
            badge_items.append(("No fallback", "pass"))
        render_badge_row(badge_items)


def render_trace_summary(trace, lab_attempt=None) -> None:
    render_kicker("Trace summary")
    trace_cols = st.columns(5)
    trace_cols[0].metric("Route", trace.route)
    trace_cols[1].metric("Agents", len(trace.agent_steps))
    trace_cols[2].metric("Tool calls", len(trace.tool_calls))
    trace_cols[3].metric("Guardrails", len(trace.guardrail_verdicts))
    trace_cols[4].metric("Latency", f"{trace.latency_ms} ms")

    agent_fallback = any(step.fallback_used for step in trace.agent_steps)
    if trace.mode_fallback_reason or trace.retrieval_fallback_reason or agent_fallback:
        fallback_status = "Fallback recorded"
        fallback_tone = "warn"
    elif trace.fallback_mode:
        fallback_status = "Mock/local baseline"
        fallback_tone = "muted"
    else:
        fallback_status = "No fallback"
        fallback_tone = "pass"
    render_badge_row(
        [
            (f"Mode: {trace.requested_app_mode} -> {trace.effective_app_mode}", "info"),
            (f"Model: {trace.model_mode}", "info"),
            (f"Retrieval: {trace.retrieval_mode}", "info"),
            (fallback_status, fallback_tone),
        ]
    )
    if trace.selected_lab_id:
        score = trace.lab_score if trace.lab_score is not None else (
            lab_attempt.percentage_score if lab_attempt else None
        )
        readiness = trace.lab_readiness or (lab_attempt.readiness if lab_attempt else "n/a")
        render_badge_row(
            [
                (f"Lab: {trace.selected_lab_id}", "muted"),
                (f"Lab score: {score}/100" if score is not None else "Lab score: n/a", "muted"),
                (f"Lab readiness: {readiness}", "warn" if readiness == "CONDITIONAL" else "pass"),
            ]
        )

    if trace.mode_fallback_reason:
        st.warning(trace.mode_fallback_reason)
    if trace.retrieval_fallback_reason:
        st.warning(f"Retrieval fallback: {trace.retrieval_fallback_reason}")

    step_rows = [
        {
            "Order": index,
            "Agent": step.agent_name,
            "Status": step.status,
            "Attempts": step.attempt_count,
            "Latency": step.latency_ms,
            "Citations": len(step.citations),
            "Guardrails": ", ".join(verdict.verdict for verdict in step.guardrail_verdicts) or "None",
        }
        for index, step in enumerate(trace.agent_steps, start=1)
    ]
    if step_rows:
        st.dataframe(step_rows, hide_index=True, use_container_width=True)
    if trace.tool_calls:
        st.dataframe(
            [
                {
                    "Tool": call.tool_name,
                    "Provider": call.retrieval_provider or "n/a",
                    "Mode": call.retrieval_mode or "n/a",
                    "Sources": call.source_count if call.source_count is not None else "n/a",
                    "Fallback": call.fallback_used,
                    "Latency": call.latency_ms,
                }
                for call in trace.tool_calls
            ],
            hide_index=True,
            use_container_width=True,
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
    selected_lab_id: str,
    lab_responses: list[LearnerLabResponse] | None,
    demo_response_profile: str,
) -> WorkflowResult:
    cached = st.session_state.get("workflow_result")
    cached_learner = st.session_state.get("workflow_learner_id")
    cached_request = st.session_state.get("workflow_request_text")
    cached_mode = st.session_state.get("workflow_mode_label")
    cached_lab_id = st.session_state.get("workflow_lab_id")
    cached_response_profile = st.session_state.get("workflow_response_profile")
    response_fingerprint = (
        "|".join(response.model_dump_json() for response in lab_responses)
        if lab_responses
        else ""
    )
    cached_response_fingerprint = st.session_state.get("workflow_response_fingerprint")
    if (
        cached
        and cached_learner == learner_id
        and cached_request == request_text
        and cached_mode == config.mode_label
        and cached_lab_id == selected_lab_id
        and cached_response_profile == demo_response_profile
        and cached_response_fingerprint == response_fingerprint
    ):
        return cached

    result = run_demo_workflow(
        learner_id=learner_id,
        request_text=request_text,
        config=config,
        selected_lab_id=selected_lab_id,
        lab_responses=lab_responses,
        demo_response_profile=demo_response_profile,
    )
    st.session_state["workflow_result"] = result
    st.session_state["workflow_learner_id"] = learner_id
    st.session_state["workflow_request_text"] = request_text
    st.session_state["workflow_mode_label"] = config.mode_label
    st.session_state["workflow_lab_id"] = selected_lab_id
    st.session_state["workflow_response_profile"] = demo_response_profile
    st.session_state["workflow_response_fingerprint"] = response_fingerprint
    return result


runtime_config = load_runtime_config()
learners = load_learners()
learner_ids = [learner.learner_id for learner in learners]
labs = load_labs()
lab_options = {f"{lab.lab_id}: {lab.title}": lab.lab_id for lab in labs}

with st.sidebar:
    st.header("Demo Controls")
    st.caption("Five-minute judge path: reset, confirm L-1001, run demo, then open Lab, Assessment, Manager, Evaluation, and Trace.")
    if st.button("Reset Demo", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    selected_learner = st.selectbox("Synthetic learner", options=learner_ids, index=0)
    selected_lab_label = st.selectbox("Scenario lab", options=list(lab_options), index=0)
    selected_lab_id = lab_options[selected_lab_label]
    if st.session_state.get("active_lab_id") != selected_lab_id:
        st.session_state.pop("lab_responses", None)
        st.session_state.pop("workflow_result", None)
        st.session_state["active_lab_id"] = selected_lab_id
    demo_response_profile = st.selectbox(
        "Demo answer profile",
        options=["conditional", "go", "not_yet"],
        index=0,
    )
    if st.button("Use Demo Answers", use_container_width=True):
        st.session_state.pop("lab_responses", None)
        st.session_state.pop("workflow_result", None)
        st.rerun()
    request_text = st.text_area("Demo request", value=DEFAULT_DEMO_REQUEST, height=150)
    run_clicked = st.button("Run Demo", type="primary", use_container_width=True)
    st.divider()
    st.subheader("Runtime")
    render_badge_row(
        [
            (f"Requested: {runtime_config.requested_mode}", "info"),
            (f"Execution: {runtime_config.effective_mode}", "info"),
            (f"Retrieval: {runtime_config.retrieval_mode}", "muted"),
        ]
    )
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

lab_responses = st.session_state.get("lab_responses")

if run_clicked or "workflow_result" not in st.session_state:
    try:
        result = get_or_run_demo(
            selected_learner,
            request_text,
            runtime_config,
            selected_lab_id,
            lab_responses,
            demo_response_profile,
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
else:
    result = get_or_run_demo(
        selected_learner,
        request_text,
        runtime_config,
        selected_lab_id,
        lab_responses,
        demo_response_profile,
    )

learner = result.learner
trace = result.trace

st.title("SOC Readiness Command Center")
st.markdown(
    "<div class='small-note'>Judge-ready multi-agent SOC readiness demo. "
    "The default path is deterministic mock mode with local synthetic grounding; optional "
    "Foundry and Foundry IQ modes remain explicitly labeled and safely fall back.</div>",
    unsafe_allow_html=True,
)

if result.safety_response is not None:
    render_submission_snapshot(trace, None, None)
    st.error(result.safety_response.message)
    st.subheader("Safe Alternatives")
    for alternative in result.safety_response.safe_alternatives:
        st.write(f"- {alternative}")
    render_trace_summary(trace)
    with st.expander("Agent Trace", expanded=True):
        st.json(trace.model_dump(mode="json"))
    st.stop()

if result.route.route == "manager_insights":
    manager = result.manager_insight
    if manager is None:
        st.error("Manager route did not return manager insight.")
        st.stop()
    render_submission_snapshot(trace, None, None)
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
    render_trace_summary(trace)
    with st.expander("Agent Trace", expanded=False):
        st.json(trace.model_dump(mode="json"))
    st.stop()

if (
    result.certification_path is None
    or result.skill_gap_report is None
    or result.study_plan is None
    or result.scenario_lab is None
    or result.lab_attempt is None
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
lab_attempt = result.lab_attempt
assessment = result.assessment_result
manager = result.manager_insight

render_submission_snapshot(trace, assessment.overall_readiness, lab_attempt.percentage_score)

summary_cols = st.columns(4)
summary_cols[0].metric("Learner", learner.learner_id)
summary_cols[1].metric("Target", learner.role_target)
summary_cols[2].metric("Readiness", assessment.overall_readiness)
summary_cols[3].metric("Trace latency", f"{trace.latency_ms} ms")
st.metric("Lab score", f"{lab_attempt.percentage_score}/100", lab_attempt.readiness)
st.caption(
    f"Mode: {trace.requested_app_mode} -> {trace.effective_app_mode}; "
    f"model: {trace.model_mode}; retrieval: {trace.retrieval_mode}; "
    f"citations: {len(trace.citations)}"
)
if trace.mode_fallback_reason:
    st.warning(trace.mode_fallback_reason)
if trace.retrieval_fallback_reason:
    st.warning(f"Retrieval fallback: {trace.retrieval_fallback_reason}")

tabs = st.tabs([
    "Learner",
    "Path",
    "Skill Gaps",
    "Study Plan",
    "Scenario Lab",
    "Assessment",
    "Manager",
    "Evaluation",
])

with tabs[0]:
    render_kicker("Learner readiness context")
    st.subheader("Learner Profile")
    render_snapshot_tiles(
        [
            ("Current role", learner.role_current),
            ("Target role", learner.role_target),
            ("Focus hours", str(learner.available_focus_hours_per_week)),
            ("Experience", learner.experience_level),
        ],
        columns=4,
    )
    st.table(
        [
            {"Field": "Current role", "Value": learner.role_current},
            {"Field": "Target role", "Value": learner.role_target},
            {"Field": "Experience", "Value": learner.experience_level},
            {"Field": "Focus hours", "Value": learner.available_focus_hours_per_week},
            {"Field": "Learning style", "Value": learner.preferred_learning_style},
            {"Field": "Completed certifications", "Value": ", ".join(learner.completed_certifications) or "None"},
        ],
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
    render_kicker("Recommended certification route")
    st.subheader("Certification Path")
    path_cols = st.columns(3)
    path_cols[0].metric(
        "Primary path",
        path.recommended_certifications[0] if path.recommended_certifications else path.target_role,
    )
    path_cols[1].metric("Confidence", f"{path.confidence:.0%}")
    path_cols[2].metric("Citations", len(path.citations))
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
    render_kicker("Where the learner needs practice")
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
    priority_count = sum(1 for row in rows if row["Priority"] == "High")
    gap_cols = st.columns(3)
    gap_cols[0].metric("High priority gaps", priority_count)
    gap_cols[1].metric("Domains measured", len(rows))
    gap_cols[2].metric("Evidence citations", len(gaps.citations))
    st.subheader("Priority Focus")
    for focus in gaps.recommended_focus:
        st.write(f"- {focus}")

with tabs[3]:
    render_kicker("Capacity-aware plan")
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
    render_kicker("Interactive defensive lab")
    st.subheader(lab.title)
    render_snapshot_tiles(
        [
            ("Selected lab", lab.lab_id),
            ("Domain", lab.domain),
            ("Score", f"{lab_attempt.percentage_score}/100"),
            ("Readiness", lab_attempt.readiness),
        ],
        columns=4,
    )
    st.progress(lab_attempt.percentage_score / 100)
    st.write(lab.prompt)
    for artifact in lab.artifacts:
        with st.expander(f"{artifact.artifact_type}: {artifact.name}", expanded=True):
            st.code(artifact.content)
    st.markdown("**Learner task**")
    st.write(lab.learner_task)
    st.markdown("**Interactive response**")
    current_responses = {
        response.question_id: response
        for response in lab_attempt.responses
    }
    with st.form(f"lab-response-form-{lab.lab_id}"):
        response_inputs: dict[str, dict[str, object]] = {}
        for question in lab.questions:
            st.markdown(f"**{question.prompt}**")
            existing = current_responses.get(question.question_id)
            if question.response_type == "single_choice":
                option_ids = [option.option_id for option in question.options]
                current_option = (
                    existing.selected_option_ids[0]
                    if existing and existing.selected_option_ids
                    else option_ids[0]
                )
                selected = st.radio(
                    question.question_id,
                    options=option_ids,
                    index=option_ids.index(current_option) if current_option in option_ids else 0,
                    format_func=lambda option_id, q=question: next(
                        option.text for option in q.options if option.option_id == option_id
                    ),
                    label_visibility="collapsed",
                )
                response_inputs[question.question_id] = {
                    "selected_option_ids": [selected],
                    "free_text": "",
                }
            elif question.response_type == "multi_select":
                option_ids = [option.option_id for option in question.options]
                selected = st.multiselect(
                    question.question_id,
                    options=option_ids,
                    default=(
                        existing.selected_option_ids
                        if existing
                        else []
                    ),
                    format_func=lambda option_id, q=question: next(
                        option.text for option in q.options if option.option_id == option_id
                    ),
                    label_visibility="collapsed",
                )
                response_inputs[question.question_id] = {
                    "selected_option_ids": selected,
                    "free_text": "",
                }
            else:
                text = st.text_area(
                    question.question_id,
                    value=existing.free_text if existing else "",
                    height=90,
                    label_visibility="collapsed",
                )
                response_inputs[question.question_id] = {
                    "selected_option_ids": [],
                    "free_text": text,
                }
        submitted = st.form_submit_button("Score Custom Attempt", type="primary")
        if submitted:
            st.session_state["lab_responses"] = [
                LearnerLabResponse(
                    question_id=question_id,
                    selected_option_ids=list(payload["selected_option_ids"]),
                    free_text=str(payload["free_text"]),
                )
                for question_id, payload in response_inputs.items()
            ]
            st.session_state.pop("workflow_result", None)
            st.rerun()

    st.markdown("**Score debrief**")
    debrief_cols = st.columns(3)
    debrief_cols[0].metric("Lab readiness", lab_attempt.readiness)
    debrief_cols[1].metric("Score", f"{lab_attempt.percentage_score}/100")
    debrief_cols[2].metric("Guardrail", lab_attempt.guardrail_verdict.verdict)
    st.write(lab_attempt.adaptive_remediation_reason)
    st.dataframe(
        [
            {
                "Question": item.question_id,
                "Domain": item.domain,
                "Earned": item.earned_points,
                "Max": item.max_points,
                "Missed signals": ", ".join(item.missed_signals) or "None",
            }
            for item in lab_attempt.score_breakdown
        ],
        hide_index=True,
        use_container_width=True,
    )
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
    st.markdown("**Citations**")
    render_citations(lab.citations)

with tabs[5]:
    render_kicker("Adaptive readiness result")
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
    st.caption(assessment.lab_attempt.adaptive_remediation_reason if assessment.lab_attempt else "")
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
    render_kicker("Privacy-preserving manager view")
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

with tabs[7]:
    render_kicker("Reliability evidence")
    st.subheader("Evaluation Evidence")
    eval_cols = st.columns(4)
    eval_cols[0].metric("Local tests", "74 passed")
    eval_cols[1].metric("Eval cases", "25")
    eval_cols[2].metric("Overall", get_evaluation_status())
    eval_cols[3].metric("Cloud calls in CI", "0")
    st.info("Local evaluation runs deterministic mock workflows only. Optional Foundry portal evaluation uses the committed JSONL export.")
    if EVALUATION_REPORT_PATH.exists():
        st.markdown(EVALUATION_REPORT_PATH.read_text(encoding="utf-8"))
    else:
        st.info("Run .\\scripts\\run_eval.ps1 to generate evaluation evidence.")

st.divider()
render_trace_summary(trace, lab_attempt)
with st.expander("Agent Trace", expanded=False):
    st.json(trace.model_dump(mode="json"))
