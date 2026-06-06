from __future__ import annotations

import json
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .lab_scoring import PROFILE_CONDITIONAL, score_lab_attempt
from .loader import DEFAULT_LAB_ID, get_lab
from .schemas import (
    AgentStep,
    AssessmentResult,
    CertificationPath,
    EvidenceBundle,
    GuardrailVerdict,
    LabAttempt,
    ManagerInsight,
    RouteDecision,
    RunTrace,
    SafetyResponse,
    ScenarioLab,
    SkillGapReport,
    StudyPlan,
)


T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class AgentResult(Generic[T]):
    raw_json: str
    parsed: T


def parse_agent_json(raw_json: str, schema: type[T]) -> T:
    if not isinstance(raw_json, str):
        raise TypeError("Mock agents must return raw JSON strings before parsing.")
    return schema.model_validate_json(raw_json)


class DeterministicMockAgent(Generic[T]):
    name: str
    output_schema: type[T]
    latency_ms: int

    def raw_response(self, context: Any | None = None) -> str:
        raise NotImplementedError

    def run(self, trace: RunTrace, input_summary: str) -> AgentResult[T]:
        raw_json = self.raw_response()
        parsed = parse_agent_json(raw_json, self.output_schema)
        citations = list(getattr(parsed, "citations", []))
        guardrails = [parsed] if isinstance(parsed, GuardrailVerdict) else []
        retrieval_mode = getattr(parsed, "retrieval_mode", None)

        trace.agent_steps.append(
            AgentStep(
                agent_name=self.name,
                latency_ms=self.latency_ms,
                input_summary=input_summary,
                raw_json_response=raw_json,
                parsed_output=parsed.model_dump(mode="json"),
                citations=citations,
                guardrail_verdicts=guardrails,
                retrieval_mode=retrieval_mode,
            )
        )
        trace.latency_ms += self.latency_ms
        trace.citations.extend(citations)
        trace.guardrail_verdicts.extend(guardrails)
        return AgentResult(raw_json=raw_json, parsed=parsed)


class MockIntakeRouterAgent(DeterministicMockAgent[RouteDecision]):
    name = "Intake Router Agent"
    output_schema = RouteDecision
    latency_ms = 342

    def raw_response(self, context: Any | None = None) -> str:
        request_text = getattr(context, "request_text", "") if context is not None else ""
        input_guardrail = getattr(context, "input_guardrail", None) if context is not None else None
        learner_id = getattr(getattr(context, "learner", None), "learner_id", "L-1001")

        if input_guardrail is not None and input_guardrail.verdict == "blocked":
            issues = '", "'.join(input_guardrail.issues)
            return dedent(
                f"""
                {{
                  "route": "safety_refusal",
                  "learner_id": "{learner_id}",
                  "goal": "Refuse unsafe request and redirect to defensive synthetic learning.",
                  "risk_flags": ["{issues}"],
                  "next_agents": ["Safety Refusal Agent", "Verifier and Safety Agent"],
                  "confidence": 0.99
                }}
                """
            ).strip()

        manager_terms = ("manager", "team", "dashboard", "capacity", "readiness distribution")
        if any(term in request_text.lower() for term in manager_terms):
            return dedent(
                f"""
                {{
                  "route": "manager_insights",
                  "learner_id": "{learner_id}",
                  "goal": "Produce aggregate team readiness and capacity insight.",
                  "risk_flags": [],
                  "next_agents": ["Knowledge Curator Agent", "Manager Insights Agent", "Verifier and Safety Agent"],
                  "confidence": 0.96
                }}
                """
            ).strip()

        return dedent(
            f"""
            {{
              "route": "soc_readiness_demo",
              "learner_id": "{learner_id}",
              "goal": "Prepare a helpdesk analyst for SOC analyst readiness in 4 weeks.",
              "risk_flags": [],
              "next_agents": [
                "Knowledge Curator Agent",
                "Certification Path Advisor Agent",
                "Skill Gap Analyst Agent",
                "Study Plan Generator Agent",
                "Scenario Lab Coach Agent",
                "Lab Scoring Agent",
                "Assessment Agent",
                "Manager Insights Agent",
                "Verifier and Safety Agent"
              ],
              "confidence": 0.97
            }}
            """
        ).strip()


class MockKnowledgeCuratorAgent(DeterministicMockAgent[EvidenceBundle]):
    name = "Knowledge Curator Agent"
    output_schema = EvidenceBundle
    latency_ms = 842

    def raw_response(self, context: Any | None = None) -> str:
        evidence = getattr(context, "evidence", None) if context is not None else None
        if isinstance(evidence, EvidenceBundle):
            return evidence.model_dump_json(indent=2)

        return dedent(
            """
            {
              "query": "SOC analyst readiness path using Security+ foundation and SC-200 operations practice",
              "sources": [
                {
                  "source_id": "OFFICIAL-SC200",
                  "title": "Microsoft SC-200 certification overview",
                  "source_type": "official_public_summary",
                  "url": "https://learn.microsoft.com/en-us/credentials/certifications/security-operations-analyst/",
                  "excerpt": "SC-200 is positioned around Microsoft security operations analysis, including threat mitigation with Microsoft security tools.",
                  "metadata": {"certification": "SC-200"}
                },
                {
                  "source_id": "OFFICIAL-SECURITYPLUS",
                  "title": "CompTIA Security+ public certification page",
                  "source_type": "official_public_summary",
                  "url": "https://www.comptia.org/en/certifications/security/",
                  "excerpt": "Security+ is a broad cybersecurity foundation certification covering core security concepts and operations.",
                  "metadata": {"certification": "Security+"}
                },
                {
                  "source_id": "SYN-SOC-GUIDE",
                  "title": "Synthetic SOC Analyst Enablement Guide",
                  "source_type": "synthetic_internal",
                  "url": null,
                  "excerpt": "This synthetic guide maps helpdesk-to-SOC learners to alert triage, incident response, KQL interpretation, and reporting practice.",
                  "metadata": {"synthetic": "true"}
                },
                {
                  "source_id": "SYN-WORK-CAPACITY",
                  "title": "Synthetic Team Learning Capacity Report",
                  "source_type": "synthetic_policy",
                  "url": null,
                  "excerpt": "Learners with meeting-heavy weeks should keep planned study blocks within available focus hours and use short scenario checkpoints.",
                  "metadata": {"synthetic": "true"}
                }
              ],
              "snippets": [
                "SC-200 is the strongest Microsoft-aligned SOC operations anchor for this demo.",
                "Security+ provides the foundation layer for an entry-level helpdesk learner.",
                "The synthetic SOC guide adds approved internal practice domains.",
                "The synthetic capacity report constrains the study plan to 6 hours per week."
              ],
              "citations": [
                {
                  "source_id": "OFFICIAL-SC200",
                  "title": "Microsoft SC-200 certification overview",
                  "source_type": "official_public_summary",
                  "url": "https://learn.microsoft.com/en-us/credentials/certifications/security-operations-analyst/",
                  "excerpt": "SC-200 is positioned around Microsoft security operations analysis, including threat mitigation with Microsoft security tools.",
                  "metadata": {"certification": "SC-200"}
                },
                {
                  "source_id": "OFFICIAL-SECURITYPLUS",
                  "title": "CompTIA Security+ public certification page",
                  "source_type": "official_public_summary",
                  "url": "https://www.comptia.org/en/certifications/security/",
                  "excerpt": "Security+ is a broad cybersecurity foundation certification covering core security concepts and operations.",
                  "metadata": {"certification": "Security+"}
                },
                {
                  "source_id": "SYN-SOC-GUIDE",
                  "title": "Synthetic SOC Analyst Enablement Guide",
                  "source_type": "synthetic_internal",
                  "url": null,
                  "excerpt": "This synthetic guide maps helpdesk-to-SOC learners to alert triage, incident response, KQL interpretation, and reporting practice.",
                  "metadata": {"synthetic": "true"}
                },
                {
                  "source_id": "SYN-WORK-CAPACITY",
                  "title": "Synthetic Team Learning Capacity Report",
                  "source_type": "synthetic_policy",
                  "url": null,
                  "excerpt": "Learners with meeting-heavy weeks should keep planned study blocks within available focus hours and use short scenario checkpoints.",
                  "metadata": {"synthetic": "true"}
                }
              ],
              "retrieval_mode": "local_mock",
              "confidence": 0.91,
              "missing_evidence_warning": null
            }
            """
        ).strip()


class MockCertificationPathAdvisorAgent(DeterministicMockAgent[CertificationPath]):
    name = "Certification Path Advisor Agent"
    output_schema = CertificationPath
    latency_ms = 1204

    def raw_response(self) -> str:
        return dedent(
            """
            {
              "target_role": "SOC Analyst",
              "recommended_certifications": ["CompTIA Security+ foundation", "Microsoft SC-200-oriented SOC readiness"],
              "sequence": [
                "Refresh Security+ foundation concepts",
                "Build SOC triage and incident-response habits",
                "Practice SC-200-aligned Microsoft security operations tasks",
                "Use CySA+ V4 as a future-aware secondary path after launch"
              ],
              "prerequisites": [
                "Basic networking vocabulary",
                "Core identity and access concepts",
                "Comfort reading alerts, logs, and short incident notes"
              ],
              "rationale": "L-1001 is an entry-level helpdesk analyst targeting SOC work in 4 weeks. The best MVP path is Security+ foundation plus SC-200-oriented operations practice because it balances foundational concepts with concrete SOC tasks.",
              "caveats": [
                "CySA+ V4 launches after the hackathon submission deadline, so it is not the sole MVP anchor.",
                "This is readiness coaching, not a guarantee of passing any certification exam.",
                "All data and lab artifacts are synthetic."
              ],
              "alternate_paths": [
                "ISC2 CC for a lighter entry cybersecurity foundation",
                "CySA+ for broader analyst readiness after the V4 launch window",
                "AZ-500 as a cloud security branch with retirement caveat",
                "PenTest+ only as authorized defensive-readiness stretch content"
              ],
              "citations": [
                {
                  "source_id": "OFFICIAL-SC200",
                  "title": "Microsoft SC-200 certification overview",
                  "source_type": "official_public_summary",
                  "url": "https://learn.microsoft.com/en-us/credentials/certifications/security-operations-analyst/",
                  "excerpt": "SC-200 is positioned around Microsoft security operations analysis, including threat mitigation with Microsoft security tools.",
                  "metadata": {"certification": "SC-200"}
                },
                {
                  "source_id": "OFFICIAL-SECURITYPLUS",
                  "title": "CompTIA Security+ public certification page",
                  "source_type": "official_public_summary",
                  "url": "https://www.comptia.org/en/certifications/security/",
                  "excerpt": "Security+ is a broad cybersecurity foundation certification covering core security concepts and operations.",
                  "metadata": {"certification": "Security+"}
                }
              ],
              "confidence": 0.93
            }
            """
        ).strip()


class MockSkillGapAnalystAgent(DeterministicMockAgent[SkillGapReport]):
    name = "Skill Gap Analyst Agent"
    output_schema = SkillGapReport
    latency_ms = 965

    def raw_response(self) -> str:
        return dedent(
            """
            {
              "learner_id": "L-1001",
              "target_certification": "SC-200-oriented SOC readiness",
              "domain_scores": [
                {
                  "domain": "Security foundations",
                  "current_score": 42,
                  "target_score": 75,
                  "priority": "Medium",
                  "evidence": "Self-rating shows basic security concepts and no completed certifications.",
                  "citations": [
                    {
                      "source_id": "OFFICIAL-SECURITYPLUS",
                      "title": "CompTIA Security+ public certification page",
                      "source_type": "official_public_summary",
                      "url": "https://www.comptia.org/en/certifications/security/",
                      "excerpt": "Security+ is a broad cybersecurity foundation certification covering core security concepts and operations.",
                      "metadata": {"certification": "Security+"}
                    }
                  ]
                },
                {
                  "domain": "Incident response",
                  "current_score": 28,
                  "target_score": 78,
                  "priority": "High",
                  "evidence": "Learner has helpdesk experience but limited incident handling practice.",
                  "citations": [
                    {
                      "source_id": "SYN-SOC-GUIDE",
                      "title": "Synthetic SOC Analyst Enablement Guide",
                      "source_type": "synthetic_internal",
                      "url": null,
                      "excerpt": "This synthetic guide maps helpdesk-to-SOC learners to alert triage, incident response, KQL interpretation, and reporting practice.",
                      "metadata": {"synthetic": "true"}
                    }
                  ]
                },
                {
                  "domain": "KQL and log interpretation",
                  "current_score": 12,
                  "target_score": 70,
                  "priority": "High",
                  "evidence": "Learner self-rated KQL as 0 and needs guided query reading practice.",
                  "citations": [
                    {
                      "source_id": "SYN-SOC-GUIDE",
                      "title": "Synthetic SOC Analyst Enablement Guide",
                      "source_type": "synthetic_internal",
                      "url": null,
                      "excerpt": "This synthetic guide maps helpdesk-to-SOC learners to alert triage, incident response, KQL interpretation, and reporting practice.",
                      "metadata": {"synthetic": "true"}
                    }
                  ]
                },
                {
                  "domain": "Alert triage",
                  "current_score": 35,
                  "target_score": 80,
                  "priority": "High",
                  "evidence": "Helpdesk background helps with ticket handling, but SOC triage needs scenario practice.",
                  "citations": [
                    {
                      "source_id": "SYN-TRIAGE-PLAYBOOK",
                      "title": "Synthetic Incident Triage Playbook",
                      "source_type": "synthetic_internal",
                      "url": null,
                      "excerpt": "Use synthetic alerts to practice severity, scope, containment, evidence preservation, and escalation decisions.",
                      "metadata": {"synthetic": "true"}
                    }
                  ]
                }
              ],
              "priority_gaps": ["Incident response", "KQL and log interpretation", "Alert triage"],
              "strengths": ["Customer communication", "Ticket discipline", "Basic networking vocabulary"],
              "risk_level": "Medium",
              "recommended_focus": [
                "Short daily SOC triage drills",
                "KQL reading practice before writing practice",
                "Weekly incident-response debrief"
              ],
              "citations": [
                {
                  "source_id": "SYN-SOC-GUIDE",
                  "title": "Synthetic SOC Analyst Enablement Guide",
                  "source_type": "synthetic_internal",
                  "url": null,
                  "excerpt": "This synthetic guide maps helpdesk-to-SOC learners to alert triage, incident response, KQL interpretation, and reporting practice.",
                  "metadata": {"synthetic": "true"}
                }
              ],
              "confidence": 0.9
            }
            """
        ).strip()


class MockStudyPlanGeneratorAgent(DeterministicMockAgent[StudyPlan]):
    name = "Study Plan Generator Agent"
    output_schema = StudyPlan
    latency_ms = 1560

    def raw_response(self) -> str:
        return dedent(
            """
            {
              "learner_id": "L-1001",
              "duration_weeks": 4,
              "weekly_modules": [
                {
                  "week": 1,
                  "theme": "SOC foundations and alert triage",
                  "total_hours": 5.5,
                  "tasks": [
                    {
                      "day": "Monday",
                      "title": "Review Security+ foundation concepts for SOC work",
                      "duration_minutes": 75,
                      "activity_type": "reading",
                      "outcome": "Explain CIA, identity basics, and common alert types.",
                      "citations": [
                        {
                          "source_id": "OFFICIAL-SECURITYPLUS",
                          "title": "CompTIA Security+ public certification page",
                          "source_type": "official_public_summary",
                          "url": "https://www.comptia.org/en/certifications/security/",
                          "excerpt": "Security+ is a broad cybersecurity foundation certification covering core security concepts and operations.",
                          "metadata": {"certification": "Security+"}
                        }
                      ]
                    },
                    {
                      "day": "Thursday",
                      "title": "Triage synthetic suspicious sign-in alerts",
                      "duration_minutes": 90,
                      "activity_type": "lab",
                      "outcome": "Classify severity and identify first containment action.",
                      "citations": [
                        {
                          "source_id": "SYN-TRIAGE-PLAYBOOK",
                          "title": "Synthetic Incident Triage Playbook",
                          "source_type": "synthetic_internal",
                          "url": null,
                          "excerpt": "Use synthetic alerts to practice severity, scope, containment, evidence preservation, and escalation decisions.",
                          "metadata": {"synthetic": "true"}
                        }
                      ]
                    }
                  ],
                  "scenario_lab": "Suspicious sign-in investigation",
                  "checkpoint": "Can identify likely account compromise indicators and evidence to preserve."
                },
                {
                  "week": 2,
                  "theme": "Incident response and evidence handling",
                  "total_hours": 6.0,
                  "tasks": [
                    {
                      "day": "Tuesday",
                      "title": "Map triage notes to incident-response stages",
                      "duration_minutes": 90,
                      "activity_type": "practice",
                      "outcome": "Separate containment, eradication, recovery, and lessons learned.",
                      "citations": [
                        {
                          "source_id": "SYN-TRIAGE-PLAYBOOK",
                          "title": "Synthetic Incident Triage Playbook",
                          "source_type": "synthetic_internal",
                          "url": null,
                          "excerpt": "Use synthetic alerts to practice severity, scope, containment, evidence preservation, and escalation decisions.",
                          "metadata": {"synthetic": "true"}
                        }
                      ]
                    },
                    {
                      "day": "Friday",
                      "title": "Write a synthetic incident handoff summary",
                      "duration_minutes": 60,
                      "activity_type": "review",
                      "outcome": "Produce a manager-safe summary without exposing personal details.",
                      "citations": [
                        {
                          "source_id": "SYN-MANAGER-BRIEF",
                          "title": "Synthetic Manager Readiness Dashboard Brief",
                          "source_type": "synthetic_policy",
                          "url": null,
                          "excerpt": "Manager summaries should aggregate readiness and capacity patterns without exposing private learner weaknesses.",
                          "metadata": {"synthetic": "true"}
                        }
                      ]
                    }
                  ],
                  "scenario_lab": "Phishing mailbox triage",
                  "checkpoint": "Can preserve evidence and recommend proportionate containment."
                },
                {
                  "week": 3,
                  "theme": "Threat hunting and KQL interpretation",
                  "total_hours": 6.0,
                  "tasks": [
                    {
                      "day": "Monday",
                      "title": "Read KQL-like query patterns from synthetic logs",
                      "duration_minutes": 90,
                      "activity_type": "practice",
                      "outcome": "Explain filters, joins, and time windows in plain language.",
                      "citations": [
                        {
                          "source_id": "SYN-SOC-GUIDE",
                          "title": "Synthetic SOC Analyst Enablement Guide",
                          "source_type": "synthetic_internal",
                          "url": null,
                          "excerpt": "This synthetic guide maps helpdesk-to-SOC learners to alert triage, incident response, KQL interpretation, and reporting practice.",
                          "metadata": {"synthetic": "true"}
                        }
                      ]
                    },
                    {
                      "day": "Thursday",
                      "title": "Hunt for impossible-travel indicators in synthetic events",
                      "duration_minutes": 90,
                      "activity_type": "lab",
                      "outcome": "Identify the suspicious sequence and name the next evidence source.",
                      "citations": [
                        {
                          "source_id": "SYN-SIGNIN-LAB",
                          "title": "Synthetic Suspicious Sign-in Lab",
                          "source_type": "synthetic_lab",
                          "url": null,
                          "excerpt": "The lab uses documentation-reserved IP addresses and fictional identities to simulate suspicious sign-in triage.",
                          "metadata": {"synthetic": "true"}
                        }
                      ]
                    }
                  ],
                  "scenario_lab": "KQL interpretation mini-task",
                  "checkpoint": "Can explain why a query surfaces a suspicious identity sequence."
                },
                {
                  "week": 4,
                  "theme": "Mock assessment and remediation sprint",
                  "total_hours": 5.5,
                  "tasks": [
                    {
                      "day": "Tuesday",
                      "title": "Complete readiness assessment",
                      "duration_minutes": 90,
                      "activity_type": "assessment",
                      "outcome": "Receive GO, CONDITIONAL, or NOT_YET readiness verdict.",
                      "citations": [
                        {
                          "source_id": "OFFICIAL-SC200",
                          "title": "Microsoft SC-200 certification overview",
                          "source_type": "official_public_summary",
                          "url": "https://learn.microsoft.com/en-us/credentials/certifications/security-operations-analyst/",
                          "excerpt": "SC-200 is positioned around Microsoft security operations analysis, including threat mitigation with Microsoft security tools.",
                          "metadata": {"certification": "SC-200"}
                        }
                      ]
                    },
                    {
                      "day": "Friday",
                      "title": "Run targeted remediation sprint",
                      "duration_minutes": 90,
                      "activity_type": "review",
                      "outcome": "Close the top two gaps before final practice.",
                      "citations": [
                        {
                          "source_id": "SYN-WORK-CAPACITY",
                          "title": "Synthetic Team Learning Capacity Report",
                          "source_type": "synthetic_policy",
                          "url": null,
                          "excerpt": "Learners with meeting-heavy weeks should keep planned study blocks within available focus hours and use short scenario checkpoints.",
                          "metadata": {"synthetic": "true"}
                        }
                      ]
                    }
                  ],
                  "scenario_lab": "Readiness debrief and remediation",
                  "checkpoint": "Can explain weak domains and next study action."
                }
              ],
              "workload_fit": {
                "available_focus_hours_per_week": 6,
                "planned_hours_per_week": 6.0,
                "fit": "tight",
                "rationale": "The schedule uses short focused blocks and stays within the learner's 6 weekly focus hours."
              },
              "checkpoints": [
                "Week 1 alert triage checkpoint",
                "Week 2 incident handoff checkpoint",
                "Week 3 KQL interpretation checkpoint",
                "Week 4 readiness and remediation checkpoint"
              ],
              "citations": [
                {
                  "source_id": "SYN-WORK-CAPACITY",
                  "title": "Synthetic Team Learning Capacity Report",
                  "source_type": "synthetic_policy",
                  "url": null,
                  "excerpt": "Learners with meeting-heavy weeks should keep planned study blocks within available focus hours and use short scenario checkpoints.",
                  "metadata": {"synthetic": "true"}
                },
                {
                  "source_id": "SYN-SOC-GUIDE",
                  "title": "Synthetic SOC Analyst Enablement Guide",
                  "source_type": "synthetic_internal",
                  "url": null,
                  "excerpt": "This synthetic guide maps helpdesk-to-SOC learners to alert triage, incident response, KQL interpretation, and reporting practice.",
                  "metadata": {"synthetic": "true"}
                }
              ],
              "confidence": 0.89
            }
            """
        ).strip()


class MockScenarioLabCoachAgent(DeterministicMockAgent[ScenarioLab]):
    name = "Scenario Lab Coach Agent"
    output_schema = ScenarioLab
    latency_ms = 1188

    def raw_response(self, context: Any | None = None) -> str:
        lab_id = getattr(context, "selected_lab_id", None) or DEFAULT_LAB_ID
        try:
            lab = get_lab(lab_id)
        except ValueError:
            lab = get_lab(DEFAULT_LAB_ID)
        return lab.model_dump_json(indent=2)


class MockLabScoringAgent(DeterministicMockAgent[LabAttempt]):
    name = "Lab Scoring Agent"
    output_schema = LabAttempt
    latency_ms = 733

    def raw_response(self, context: Any | None = None) -> str:
        lab = getattr(context, "scenario_lab", None) if context is not None else None
        if not isinstance(lab, ScenarioLab):
            lab = get_lab(DEFAULT_LAB_ID)
        learner = getattr(context, "learner", None) if context is not None else None
        learner_id = getattr(learner, "learner_id", "L-1001")
        responses = getattr(context, "lab_responses", None) if context is not None else None
        profile = (
            getattr(context, "demo_response_profile", PROFILE_CONDITIONAL)
            if context is not None
            else PROFILE_CONDITIONAL
        )
        attempt = score_lab_attempt(
            lab=lab,
            learner_id=learner_id,
            responses=responses,
            response_profile=profile,
        )
        return attempt.model_dump_json(indent=2)


class MockAssessmentAgent(DeterministicMockAgent[AssessmentResult]):
    name = "Assessment Agent"
    output_schema = AssessmentResult
    latency_ms = 1375

    def raw_response(self, context: Any | None = None) -> str:
        lab_attempt = getattr(context, "lab_attempt", None) if context is not None else None
        learner = getattr(context, "learner", None) if context is not None else None
        learner_id = getattr(learner, "learner_id", "L-1001")
        if isinstance(lab_attempt, LabAttempt):
            base_scores = {
                "Security foundations": 76,
                "Incident response": 68,
                "KQL and log interpretation": 58,
                "Alert triage": 74,
                "Reporting and communication": 82,
            }
            domain_scores = dict(base_scores)
            for domain, score in lab_attempt.domain_scores.items():
                baseline = base_scores.get(domain, score)
                domain_scores[domain] = round((baseline + score) / 2)

            overall_score = round((72 + lab_attempt.percentage_score) / 2)
            if lab_attempt.guardrail_verdict.verdict == "blocked":
                readiness = "NOT_YET"
            elif overall_score >= 85 and lab_attempt.readiness == "GO":
                readiness = "GO"
            elif overall_score >= 60 and lab_attempt.readiness != "NOT_YET":
                readiness = "CONDITIONAL"
            else:
                readiness = "NOT_YET"

            weak_domains = lab_attempt.remediation_focus or [
                domain for domain, score in domain_scores.items() if score < 75
            ]
            if readiness == "GO":
                recommendation = (
                    "Proceed to final review practice. Keep one short scenario lab in the plan "
                    "to maintain SOC reasoning fluency."
                )
                remediation_tasks = [
                    {
                        "title": "Final timed SOC readiness review",
                        "focus_domain": "Assessment readiness",
                        "duration_minutes": 60,
                        "outcome": "Confirm the learner can explain the lab path under time pressure.",
                    }
                ]
                success_criteria = [
                    "Maintain lab score at or above 85",
                    "Explain evidence and containment without overclaiming",
                ]
            else:
                recommendation = (
                    "Continue the SOC readiness path and complete the adaptive remediation "
                    "sprint before the final timed assessment."
                )
                remediation_tasks = [
                    {
                        "title": f"{domain} remediation drill",
                        "focus_domain": domain,
                        "duration_minutes": 45 if index else 60,
                        "outcome": f"Close missed signals for {domain}.",
                    }
                    for index, domain in enumerate(weak_domains[:3])
                ]
                success_criteria = [
                    "Score at least 75 in each remediated lab domain",
                    "Explain missed signals from the lab debrief",
                    "Keep all responses synthetic, defensive, and citation-aware",
                ]

            evidence = [
                f"Interactive lab {lab_attempt.lab_id} scored {lab_attempt.percentage_score} with {lab_attempt.readiness} lab readiness.",
                lab_attempt.adaptive_remediation_reason,
            ]
            for item in lab_attempt.score_breakdown:
                if item.missed_signals:
                    evidence.append(
                        f"{item.domain}: missed {', '.join(item.missed_signals)}"
                    )
                else:
                    evidence.append(f"{item.domain}: full credit on {item.question_id}")

            payload = {
                "learner_id": learner_id,
                "overall_readiness": readiness,
                "overall_score": overall_score,
                "domain_scores": domain_scores,
                "recommendation": recommendation,
                "evidence": evidence,
                "remediation_plan": {
                    "duration_days": 5 if readiness != "GO" else 3,
                    "tasks": remediation_tasks,
                    "success_criteria": success_criteria,
                },
                "lab_attempt": lab_attempt.model_dump(mode="json"),
                "citations": [
                    citation.model_dump(mode="json")
                    for citation in lab_attempt.citations
                ],
                "confidence": 0.9,
            }
            return json.dumps(payload, indent=2)

        return dedent(
            """
            {
              "learner_id": "L-1001",
              "overall_readiness": "CONDITIONAL",
              "overall_score": 72,
              "domain_scores": {
                "Security foundations": 76,
                "Incident response": 68,
                "KQL and log interpretation": 58,
                "Alert triage": 74,
                "Reporting and communication": 82
              },
              "recommendation": "Proceed with the SOC readiness path, but complete a focused remediation sprint before attempting a final timed assessment.",
              "evidence": [
                "Correctly classified the suspicious sign-in as likely account compromise.",
                "Named password reset but did not explicitly include session revocation.",
                "Preserved sign-in logs but initially missed mailbox audit evidence.",
                "Explained findings clearly enough for manager-safe reporting."
              ],
              "remediation_plan": {
                "duration_days": 5,
                "tasks": [
                  {
                    "title": "Session revocation and identity containment drill",
                    "focus_domain": "Incident response",
                    "duration_minutes": 60,
                    "outcome": "Name containment actions in the right order for suspected account compromise."
                  },
                  {
                    "title": "Mailbox audit evidence review",
                    "focus_domain": "Alert triage",
                    "duration_minutes": 45,
                    "outcome": "Include mailbox rules, forwarding, and audit events in evidence preservation."
                  },
                  {
                    "title": "KQL interpretation mini-check",
                    "focus_domain": "KQL and log interpretation",
                    "duration_minutes": 60,
                    "outcome": "Explain a query result without overclaiming."
                  }
                ],
                "success_criteria": [
                  "Score at least 75 on KQL interpretation",
                  "Include session revocation in containment plan",
                  "Preserve all three evidence classes in the lab debrief"
                ]
              },
              "citations": [
                {
                  "source_id": "SYN-SIGNIN-LAB",
                  "title": "Synthetic Suspicious Sign-in Lab",
                  "source_type": "synthetic_lab",
                  "url": null,
                  "excerpt": "The lab uses documentation-reserved IP addresses and fictional identities to simulate suspicious sign-in triage.",
                  "metadata": {"synthetic": "true"}
                },
                {
                  "source_id": "SYN-TRIAGE-PLAYBOOK",
                  "title": "Synthetic Incident Triage Playbook",
                  "source_type": "synthetic_internal",
                  "url": null,
                  "excerpt": "Use synthetic alerts to practice severity, scope, containment, evidence preservation, and escalation decisions.",
                  "metadata": {"synthetic": "true"}
                }
              ],
              "confidence": 0.87
            }
            """
        ).strip()


class MockManagerInsightsAgent(DeterministicMockAgent[ManagerInsight]):
    name = "Manager Insights Agent"
    output_schema = ManagerInsight
    latency_ms = 904

    def raw_response(self) -> str:
        return dedent(
            """
            {
              "team_id": "TEAM-SOC-A",
              "summary": "TEAM-SOC-A is close to SOC readiness but needs targeted support for KQL interpretation and incident containment.",
              "readiness_distribution": {
                "GO": 1,
                "CONDITIONAL": 4,
                "NOT_YET": 1
              },
              "top_skill_gaps": [
                "KQL and log interpretation",
                "Incident containment sequence",
                "Evidence preservation across identity and mailbox artifacts"
              ],
              "capacity_risk": "Medium",
              "recommended_actions": [
                "Protect two 45-minute focus blocks per learner this week.",
                "Run a group debrief on suspicious sign-in containment.",
                "Coach KQL reading before asking learners to author queries."
              ],
              "privacy_note": "All profiles are synthetic. The manager view reports aggregate patterns and avoids exposing private learner weaknesses.",
              "citations": [
                {
                  "source_id": "SYN-MANAGER-BRIEF",
                  "title": "Synthetic Manager Readiness Dashboard Brief",
                  "source_type": "synthetic_policy",
                  "url": null,
                  "excerpt": "Manager summaries should aggregate readiness and capacity patterns without exposing private learner weaknesses.",
                  "metadata": {"synthetic": "true"}
                },
                {
                  "source_id": "SYN-WORK-CAPACITY",
                  "title": "Synthetic Team Learning Capacity Report",
                  "source_type": "synthetic_policy",
                  "url": null,
                  "excerpt": "Learners with meeting-heavy weeks should keep planned study blocks within available focus hours and use short scenario checkpoints.",
                  "metadata": {"synthetic": "true"}
                }
              ],
              "confidence": 0.9
            }
            """
        ).strip()


class MockVerifierSafetyAgent(DeterministicMockAgent[GuardrailVerdict]):
    name = "Verifier and Safety Agent"
    output_schema = GuardrailVerdict
    latency_ms = 511

    def raw_response(self) -> str:
        return dedent(
            """
            {
              "verdict": "allowed",
              "issues": [],
              "rewrite_instructions": null,
              "checks": {
                "citations_present": true,
                "synthetic_data_only": true,
                "no_exam_dump_content": true,
                "defensive_cyber_framing": true,
                "no_pass_guarantee": true,
                "manager_privacy_preserved": true,
                "schemas_validated": true
              }
            }
            """
        ).strip()


class MockSafetyRefusalAgent(DeterministicMockAgent[SafetyResponse]):
    name = "Safety Refusal Agent"
    output_schema = SafetyResponse
    latency_ms = 426

    def raw_response(self, context: Any | None = None) -> str:
        guardrail = getattr(context, "input_guardrail", None) if context is not None else None
        issues = getattr(guardrail, "issues", [])
        checks = getattr(
            guardrail,
            "checks",
            {
                "no_real_pii": True,
                "no_secrets": True,
                "no_exam_dump_request": True,
                "defensive_cyber_intent": True,
            },
        )
        payload = {
            "route": "safety_refusal",
            "message": (
                "I cannot help with that request. This demo only supports defensive, "
                "synthetic cybersecurity learning and certification readiness."
            ),
            "safe_alternatives": [
                "Practice the suspicious sign-in investigation lab using synthetic artifacts.",
                "Create a defensive incident-response study plan.",
                "Review how to document and remediate a vulnerability safely.",
            ],
            "guardrail_verdict": {
                "verdict": "blocked",
                "issues": issues,
                "rewrite_instructions": (
                    "Refuse briefly and redirect to defensive, synthetic learning."
                ),
                "checks": checks,
            },
        }
        return json.dumps(payload, indent=2)
