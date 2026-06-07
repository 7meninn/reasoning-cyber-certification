import json

import pytest

from cybersecurity_readiness.evaluation import (
    DEFAULT_CASES_PATH,
    DEFAULT_FOUNDRY_EXPORT_PATH,
    build_metrics,
    export_foundry_dataset,
    load_eval_cases,
    render_markdown_report,
    run_local_evaluation,
)


def test_eval_dataset_validates_and_has_required_coverage():
    cases = load_eval_cases()

    assert len(cases) >= 20
    assert {case.category for case in cases} >= {
        "learner_planning",
        "manager_insights",
        "lab_assessment",
        "retrieval_citation",
        "fallback",
        "safety_refusal",
    }
    assert all(case.expected_route for case in cases)
    assert all(case.expected_safety in {"allowed", "blocked"} for case in cases)
    assert all(isinstance(case.citation_required, bool) for case in cases)


def test_local_eval_runner_produces_passing_deterministic_metrics():
    report = run_local_evaluation()

    assert report.case_count >= 20
    assert report.passed is True
    metrics = {metric.name: metric for metric in report.metrics}
    assert metrics["route_accuracy"].value == 1.0
    assert metrics["task_adherence"].value == 1.0
    assert metrics["safety_pass_rate"].value == 1.0
    assert metrics["citation_coverage"].value == 1.0
    assert metrics["grounded_citation_support"].value == 1.0
    assert metrics["average_trace_latency_ms"].value > 0
    assert metrics["p95_trace_latency_ms"].value >= metrics["average_trace_latency_ms"].value


def test_eval_runner_fails_when_thresholds_are_not_met():
    report = run_local_evaluation(thresholds={"route_accuracy": 1.01})

    assert report.passed is False
    metric = next(item for item in report.metrics if item.name == "route_accuracy")
    assert metric.passed is False


def test_build_metrics_can_fail_from_bad_case_result():
    report = run_local_evaluation()
    bad_result = report.results[0].model_copy(update={"route_pass": False, "task_pass": False})
    metrics = build_metrics([bad_result], {"route_accuracy": 1.0, "task_adherence": 1.0})

    assert next(item for item in metrics if item.name == "route_accuracy").passed is False
    assert next(item for item in metrics if item.name == "task_adherence").passed is False


def test_markdown_report_includes_required_judge_evidence_sections():
    report = run_local_evaluation()
    markdown = render_markdown_report(report)

    assert "task_adherence" in markdown
    assert "grounded_citation_support" in markdown
    assert "citation_coverage" in markdown
    assert "safety_pass_rate" in markdown
    assert "average_trace_latency_ms" in markdown
    assert "| Case | Category | Route | Safety | Readiness | Citations | Latency | Result |" in markdown


def test_foundry_export_is_valid_jsonl_and_sanitized(tmp_path):
    cases = load_eval_cases(DEFAULT_CASES_PATH)
    export_path = tmp_path / "foundry_dataset.jsonl"

    export_foundry_dataset(cases, export_path)

    lines = export_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(cases)
    for line in lines:
        row = json.loads(line)
        assert {"case_id", "query", "ground_truth", "expected_route", "expected_safety"} <= set(row)
        assert "api_key" not in row["query"]
        assert "DEMO_PLACEHOLDER_VALUE" not in row["query"]
        assert "pat@company.invalid" not in row["query"]


def test_committed_foundry_export_matches_dataset_shape():
    cases = load_eval_cases(DEFAULT_CASES_PATH)
    rows = [
        json.loads(line)
        for line in DEFAULT_FOUNDRY_EXPORT_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) == len(cases)
    assert all("query" in row for row in rows)
    assert all("expected_route" in row for row in rows)


def test_ci_eval_path_uses_mock_mode_without_azure_calls():
    report = run_local_evaluation()

    assert report.app_mode == "mock"
    assert all(result.retrieval_mode == "local_mock" for result in report.results if result.citation_required)
    assert all("foundry" not in result.retrieval_mode for result in report.results)
