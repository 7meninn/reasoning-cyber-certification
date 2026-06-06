from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol
from urllib.parse import quote

from .config import RuntimeConfig
from .loader import DATA_DIR
from .schemas import Citation, EvidenceBundle


class LocalMockRetrievalAdapter:
    """Deterministic replacement for Foundry IQ retrieval."""

    def __init__(
        self,
        knowledge_path: str = "knowledge_docs/sources.json",
        max_docs: int = 8,
    ) -> None:
        self.knowledge_file = DATA_DIR / knowledge_path
        self.max_docs = max_docs

    def retrieve_evidence_json(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> str:
        del filters
        with self.knowledge_file.open("r", encoding="utf-8") as handle:
            documents = json.load(handle)

        query_terms = query.lower().replace("-", " ").split()
        matches = [
            doc
            for doc in documents
            if any(
                term
                in " ".join(
                    [
                        doc.get("title", ""),
                        doc.get("summary", ""),
                        doc.get("excerpt", ""),
                        " ".join(doc.get("tags", [])),
                    ]
                ).lower().replace("-", " ")
                for term in query_terms
            )
        ]
        selected = matches[: self.max_docs] if matches else documents[: self.max_docs]
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
            "retrieval_metadata": {
                "retrieval_provider": "local_mock",
                "source_count": len(citations),
                "fallback_used": False,
            },
        }
        return json.dumps(payload, indent=2)

    def retrieve_evidence(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> EvidenceBundle:
        raw_json = self.retrieve_evidence_json(query=query, filters=filters)
        return EvidenceBundle.model_validate_json(raw_json)


class RetrievalError(RuntimeError):
    pass


@dataclass(frozen=True)
class KnowledgeBaseRetrieveResponse:
    status_code: int
    payload: dict[str, Any]
    latency_ms: int


class KnowledgeBaseRetrievalClient(Protocol):
    def retrieve(
        self,
        *,
        search_endpoint: str,
        knowledge_base_name: str,
        api_version: str,
        query: str,
        max_docs: int,
        max_output_tokens: int,
    ) -> KnowledgeBaseRetrieveResponse:
        ...


class RequestsKnowledgeBaseRetrievalClient:
    def retrieve(
        self,
        *,
        search_endpoint: str,
        knowledge_base_name: str,
        api_version: str,
        query: str,
        max_docs: int,
        max_output_tokens: int,
    ) -> KnowledgeBaseRetrieveResponse:
        try:
            import requests
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:  # pragma: no cover - depends on optional runtime deps.
            raise RetrievalError(
                "Install requests and azure-identity to use APP_MODE=foundry_iq."
            ) from exc

        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default").token
        url = (
            f"{search_endpoint.rstrip('/')}/knowledgebases/"
            f"{quote(knowledge_base_name, safe='')}/retrieve?api-version={api_version}"
        )
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": query}],
                }
            ],
            "maxOutputSize": max_output_tokens,
            "top": max_docs,
        }
        start = perf_counter()
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RetrievalError(f"Foundry IQ retrieval request failed: {exc}") from exc

        latency_ms = max(1, int((perf_counter() - start) * 1000))
        if response.status_code not in (200, 206):
            raise RetrievalError(
                f"Foundry IQ retrieval returned HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise RetrievalError("Foundry IQ retrieval returned malformed JSON.") from exc
        return KnowledgeBaseRetrieveResponse(
            status_code=response.status_code,
            payload=payload,
            latency_ms=latency_ms,
        )


class FoundryIqRetrievalAdapter:
    def __init__(
        self,
        config: RuntimeConfig,
        retrieval_client: KnowledgeBaseRetrievalClient | None = None,
        fallback_adapter: LocalMockRetrievalAdapter | None = None,
    ) -> None:
        self.config = config
        self.retrieval_client = retrieval_client or RequestsKnowledgeBaseRetrievalClient()
        self.fallback_adapter = fallback_adapter or LocalMockRetrievalAdapter(
            max_docs=config.foundry_iq_max_docs
        )

    def retrieve_evidence_json(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> str:
        evidence = self.retrieve_evidence(query=query, filters=filters)
        return evidence.model_dump_json(indent=2)

    def retrieve_evidence(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> EvidenceBundle:
        del filters
        try:
            response = self.retrieval_client.retrieve(
                search_endpoint=self._required(self.config.azure_ai_search_endpoint),
                knowledge_base_name=self._required(self.config.foundry_iq_knowledge_base),
                api_version=self.config.foundry_iq_api_version,
                query=query,
                max_docs=self.config.foundry_iq_max_docs,
                max_output_tokens=self.config.foundry_iq_max_output_tokens,
            )
            return self._map_response(query=query, response=response)
        except Exception as exc:
            return self._fallback(query=query, reason=str(exc))

    def _map_response(
        self,
        *,
        query: str,
        response: KnowledgeBaseRetrieveResponse,
    ) -> EvidenceBundle:
        snippets, citations = _extract_grounding(response.payload)
        if not citations:
            raise RetrievalError("Foundry IQ retrieval returned no citations.")

        citations = citations[: self.config.foundry_iq_max_docs]
        snippets = snippets[: self.config.foundry_iq_max_docs]
        activity_summary = _summarize_activity(response.payload.get("activity", []))
        metadata = {
            "retrieval_provider": "foundry_iq",
            "knowledge_base_name": self.config.foundry_iq_knowledge_base,
            "search_endpoint": self.config.azure_ai_search_endpoint,
            "status_code": response.status_code,
            "partial_content": response.status_code == 206,
            "source_count": len(citations),
            "activity_summary": activity_summary,
            "fallback_used": False,
            "latency_ms": response.latency_ms,
        }
        return EvidenceBundle(
            query=query,
            sources=citations,
            snippets=snippets,
            citations=citations,
            retrieval_mode="foundry_iq",
            confidence=0.82 if response.status_code == 206 else 0.9,
            missing_evidence_warning=(
                "Foundry IQ returned partial content; inspect activity metadata."
                if response.status_code == 206
                else None
            ),
            retrieval_metadata=metadata,
        )

    def _fallback(self, *, query: str, reason: str) -> EvidenceBundle:
        fallback = self.fallback_adapter.retrieve_evidence(query=query)
        metadata = {
            **fallback.retrieval_metadata,
            "retrieval_provider": "foundry_iq",
            "knowledge_base_name": self.config.foundry_iq_knowledge_base,
            "fallback_used": True,
            "fallback_reason": reason,
            "requested_retrieval_mode": "foundry_iq",
            "effective_retrieval_mode": "local_mock",
        }
        return EvidenceBundle.model_validate(
            {
                **fallback.model_dump(mode="json"),
                "missing_evidence_warning": f"Foundry IQ fallback used: {reason}",
                "retrieval_metadata": metadata,
            }
        )

    @staticmethod
    def _required(value: str | None) -> str:
        if value is None:
            raise RetrievalError("Foundry IQ configuration is incomplete.")
        return value


def _extract_grounding(payload: dict[str, Any]) -> tuple[list[str], list[Citation]]:
    documents = _documents_from_response(payload)
    references = payload.get("references", [])
    if isinstance(references, list):
        documents.extend(item for item in references if isinstance(item, dict))

    snippets: list[str] = []
    citations: list[Citation] = []
    seen: set[str] = set()
    for index, document in enumerate(documents):
        citation = _citation_from_document(document, index)
        if citation.source_id in seen:
            continue
        seen.add(citation.source_id)
        citations.append(citation)
        snippets.append(citation.excerpt)
    return snippets, citations


def _documents_from_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    response_messages = payload.get("response", [])
    documents: list[dict[str, Any]] = []
    if not isinstance(response_messages, list):
        return documents

    for message in response_messages:
        if not isinstance(message, dict):
            continue
        content_items = message.get("content", [])
        if not isinstance(content_items, list):
            continue
        for item in content_items:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            documents.extend(_parse_text_documents(text))
    return documents


def _parse_text_documents(text: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [{"ref_id": "FOUNDRY-IQ-ANSWER", "title": "Foundry IQ response", "content": text}]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return [{"ref_id": "FOUNDRY-IQ-ANSWER", "title": "Foundry IQ response", "content": str(parsed)}]


def _citation_from_document(document: dict[str, Any], index: int) -> Citation:
    source = _flatten_source_document(document)
    source_id = str(
        source.get("source_id")
        or source.get("ref_id")
        or source.get("reference_id")
        or source.get("id")
        or f"FOUNDRY-IQ-{index + 1}"
    )
    title = str(source.get("title") or source.get("source_name") or source_id)
    url = source.get("url") or source.get("source_url")
    excerpt = str(
        source.get("excerpt")
        or source.get("content")
        or source.get("text")
        or source.get("snippet")
        or title
    )
    metadata = {
        str(key): str(value)
        for key, value in source.items()
        if key not in {"content", "text", "excerpt", "snippet"} and value is not None
    }
    metadata["retrieval_provider"] = "foundry_iq"
    return Citation(
        source_id=source_id,
        title=title,
        source_type=_source_type_for(source_id=source_id, url=url),
        url=str(url) if url else None,
        excerpt=excerpt[:800],
        metadata=metadata,
    )


def _flatten_source_document(document: dict[str, Any]) -> dict[str, Any]:
    source: dict[str, Any] = dict(document)
    for key in ("source", "sourceData", "metadata", "document"):
        nested = document.get(key)
        if isinstance(nested, dict):
            source = {**nested, **source}
    return source


def _source_type_for(source_id: str, url: Any) -> str:
    text = f"{source_id} {url or ''}".lower()
    if "official" in text or "learn.microsoft.com" in text or "comptia.org" in text:
        return "official_public_summary"
    if "lab" in text:
        return "synthetic_lab"
    if "policy" in text or "manager" in text or "capacity" in text:
        return "synthetic_policy"
    return "synthetic_internal"


def _summarize_activity(activity: Any) -> list[str]:
    if not isinstance(activity, list):
        return []
    summaries: list[str] = []
    for item in activity:
        if not isinstance(item, dict):
            continue
        activity_type = item.get("type", "activity")
        source = item.get("knowledgeSourceName") or item.get("modelName")
        count = item.get("count")
        elapsed = item.get("elapsedMs")
        parts = [str(activity_type)]
        if source is not None:
            parts.append(str(source))
        if count is not None:
            parts.append(f"count={count}")
        if elapsed is not None:
            parts.append(f"{elapsed}ms")
        search_args = item.get("searchIndexArguments")
        if isinstance(search_args, dict) and search_args.get("search"):
            parts.append(f"query={search_args['search']}")
        summaries.append(" | ".join(parts))
    return summaries
