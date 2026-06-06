import json

from cybersecurity_readiness.config import load_runtime_config
from cybersecurity_readiness.retrieval import (
    FoundryIqRetrievalAdapter,
    KnowledgeBaseRetrieveResponse,
    LocalMockRetrievalAdapter,
)
from cybersecurity_readiness.schemas import EvidenceBundle


def test_local_mock_retrieval_returns_valid_evidence_bundle():
    adapter = LocalMockRetrievalAdapter()

    raw_json = adapter.retrieve_evidence_json("SOC Analyst SC-200 capacity")
    assert isinstance(raw_json, str)
    assert isinstance(json.loads(raw_json), dict)

    evidence = adapter.retrieve_evidence("SOC Analyst SC-200 capacity")
    assert isinstance(evidence, EvidenceBundle)
    assert evidence.retrieval_mode == "local_mock"
    assert evidence.citations
    assert {citation.source_id for citation in evidence.citations} & {
        "OFFICIAL-SC200",
        "SYN-SOC-GUIDE",
        "SYN-WORK-CAPACITY",
    }
    assert evidence.retrieval_metadata["retrieval_provider"] == "local_mock"


def make_foundry_iq_config():
    return load_runtime_config(
        {
            "APP_MODE": "foundry_iq",
            "AZURE_AI_PROJECT_ENDPOINT": "https://demo.services.ai.azure.com/api/projects/readiness",
            "AZURE_AI_MODEL_DEPLOYMENT": "gpt-4o-mini",
            "AZURE_AI_SEARCH_ENDPOINT": "https://demo.search.windows.net",
            "FOUNDRY_IQ_KNOWLEDGE_BASE": "soc-readiness-kb",
        }
    )


def foundry_iq_payload():
    return {
        "response": [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            [
                                {
                                    "ref_id": "OFFICIAL-SC200",
                                    "title": "Microsoft SC-200 certification overview",
                                    "content": "SC-200 focuses on Microsoft security operations analysis.",
                                    "url": "https://learn.microsoft.com/en-us/credentials/certifications/security-operations-analyst/",
                                },
                                {
                                    "ref_id": "SYN-SOC-GUIDE",
                                    "title": "Synthetic SOC Analyst Enablement Guide",
                                    "content": "Synthetic SOC practice covers alert triage, KQL, and reporting.",
                                },
                            ]
                        ),
                    }
                ],
            }
        ],
        "activity": [
            {
                "type": "searchIndex",
                "knowledgeSourceName": "soc-readiness-sources",
                "count": 2,
                "elapsedMs": 41,
                "searchIndexArguments": {"search": "SOC analyst readiness"},
            }
        ],
    }


class FakeKnowledgeBaseClient:
    def __init__(self, response: KnowledgeBaseRetrieveResponse | Exception) -> None:
        self.response = response
        self.calls = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_foundry_iq_retrieval_maps_valid_response_to_evidence_bundle():
    fake_client = FakeKnowledgeBaseClient(
        KnowledgeBaseRetrieveResponse(
            status_code=200,
            payload=foundry_iq_payload(),
            latency_ms=123,
        )
    )
    adapter = FoundryIqRetrievalAdapter(make_foundry_iq_config(), retrieval_client=fake_client)

    evidence = adapter.retrieve_evidence("SOC analyst readiness")

    assert evidence.retrieval_mode == "foundry_iq"
    assert evidence.retrieval_metadata["retrieval_provider"] == "foundry_iq"
    assert evidence.retrieval_metadata["knowledge_base_name"] == "soc-readiness-kb"
    assert evidence.retrieval_metadata["status_code"] == 200
    assert evidence.retrieval_metadata["source_count"] == 2
    assert evidence.retrieval_metadata["fallback_used"] is False
    assert "searchIndex" in evidence.retrieval_metadata["activity_summary"][0]
    assert {citation.source_id for citation in evidence.citations} == {
        "OFFICIAL-SC200",
        "SYN-SOC-GUIDE",
    }
    assert fake_client.calls[0]["knowledge_base_name"] == "soc-readiness-kb"


def test_foundry_iq_retrieval_records_partial_content():
    fake_client = FakeKnowledgeBaseClient(
        KnowledgeBaseRetrieveResponse(
            status_code=206,
            payload=foundry_iq_payload(),
            latency_ms=88,
        )
    )
    adapter = FoundryIqRetrievalAdapter(make_foundry_iq_config(), retrieval_client=fake_client)

    evidence = adapter.retrieve_evidence("SOC analyst readiness")

    assert evidence.retrieval_mode == "foundry_iq"
    assert evidence.confidence == 0.82
    assert evidence.missing_evidence_warning is not None
    assert evidence.retrieval_metadata["partial_content"] is True


def test_foundry_iq_empty_citations_falls_back_to_local_mock():
    fake_client = FakeKnowledgeBaseClient(
        KnowledgeBaseRetrieveResponse(status_code=200, payload={"response": []}, latency_ms=10)
    )
    adapter = FoundryIqRetrievalAdapter(make_foundry_iq_config(), retrieval_client=fake_client)

    evidence = adapter.retrieve_evidence("SOC analyst readiness")

    assert evidence.retrieval_mode == "local_mock"
    assert evidence.retrieval_metadata["fallback_used"] is True
    assert "no citations" in evidence.retrieval_metadata["fallback_reason"]


def test_foundry_iq_malformed_response_falls_back_to_local_mock():
    fake_client = FakeKnowledgeBaseClient(
        KnowledgeBaseRetrieveResponse(
            status_code=200,
            payload={"response": [{"content": "wrong-shape"}]},
            latency_ms=10,
        )
    )
    adapter = FoundryIqRetrievalAdapter(make_foundry_iq_config(), retrieval_client=fake_client)

    evidence = adapter.retrieve_evidence("SOC analyst readiness")

    assert evidence.retrieval_mode == "local_mock"
    assert evidence.retrieval_metadata["fallback_used"] is True


def test_foundry_iq_auth_failure_falls_back_to_local_mock():
    adapter = FoundryIqRetrievalAdapter(
        make_foundry_iq_config(),
        retrieval_client=FakeKnowledgeBaseClient(RuntimeError("403 forbidden")),
    )

    evidence = adapter.retrieve_evidence("SOC analyst readiness")

    assert evidence.retrieval_mode == "local_mock"
    assert "403 forbidden" in evidence.retrieval_metadata["fallback_reason"]


def test_foundry_iq_timeout_falls_back_to_local_mock():
    adapter = FoundryIqRetrievalAdapter(
        make_foundry_iq_config(),
        retrieval_client=FakeKnowledgeBaseClient(TimeoutError("request timed out")),
    )

    evidence = adapter.retrieve_evidence("SOC analyst readiness")

    assert evidence.retrieval_mode == "local_mock"
    assert "request timed out" in evidence.retrieval_metadata["fallback_reason"]
