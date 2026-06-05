import json

from cybersecurity_readiness.retrieval import LocalMockRetrievalAdapter
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

