from __future__ import annotations

import json
from typing import Any

from .loader import DATA_DIR
from .schemas import EvidenceBundle


class LocalMockRetrievalAdapter:
    """Deterministic replacement for Foundry IQ retrieval in Phase 1."""

    def __init__(self, knowledge_path: str = "knowledge_docs/sources.json") -> None:
        self.knowledge_file = DATA_DIR / knowledge_path

    def retrieve_evidence_json(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> str:
        del filters
        with self.knowledge_file.open("r", encoding="utf-8") as handle:
            documents = json.load(handle)

        query_terms = query.lower().split()
        matches = [
            doc
            for doc in documents
            if any(term in " ".join(doc.get("tags", [])).lower() for term in query_terms)
        ]
        selected = matches[:4] if matches else documents[:4]
        citations = [
            {
                "source_id": doc["source_id"],
                "title": doc["title"],
                "source_type": doc["source_type"],
                "url": doc.get("url"),
                "excerpt": doc["excerpt"],
                "metadata": doc.get("metadata", {}),
            }
            for doc in selected
        ]
        payload = {
            "query": query,
            "sources": citations,
            "snippets": [doc["summary"] for doc in selected],
            "citations": citations,
            "retrieval_mode": "local_mock",
            "confidence": 0.88 if matches else 0.72,
            "missing_evidence_warning": None,
        }
        return json.dumps(payload, indent=2)

    def retrieve_evidence(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> EvidenceBundle:
        raw_json = self.retrieve_evidence_json(query=query, filters=filters)
        return EvidenceBundle.model_validate_json(raw_json)

