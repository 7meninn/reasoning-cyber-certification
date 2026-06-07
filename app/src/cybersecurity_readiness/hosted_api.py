from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from os import environ
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError

from .config import RuntimeConfig, load_runtime_config
from .constants import DEFAULT_DEMO_REQUEST
from .schemas import LearnerLabResponse
from .workflow import run_demo_workflow


DEFAULT_HOSTED_AGENT_API_PORT = 8000


class HostedInvokeRequest(BaseModel):
    learner_id: str = "L-1001"
    request_text: str = DEFAULT_DEMO_REQUEST
    selected_lab_id: str | None = None
    lab_responses: list[LearnerLabResponse] | None = None
    demo_response_profile: Literal["conditional", "go", "not_yet"] = "conditional"


class HostedApiError(Exception):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(message)


def health_payload(config: RuntimeConfig | None = None) -> dict[str, Any]:
    config = config or load_runtime_config()
    return {
        "service": "cybersecurity-readiness-hosted-agent",
        "status": "ok",
        "requested_mode": config.requested_mode,
        "effective_mode": config.effective_mode,
        "model_mode": config.model_mode,
        "retrieval_mode": config.retrieval_mode,
        "model_deployment_configured": config.azure_ai_model_deployment is not None,
        "foundry_project_configured": config.azure_ai_project_endpoint is not None,
        "search_endpoint_configured": config.azure_ai_search_endpoint is not None,
        "knowledge_base_configured": config.foundry_iq_knowledge_base is not None,
        "live_config_ready": config.requested_mode == config.effective_mode
        and config.effective_mode in ("foundry", "foundry_iq"),
        "fallback_reason": config.fallback_reason,
        "auth": "DefaultAzureCredential",
    }


def invoke_payload(payload: dict[str, Any], config: RuntimeConfig | None = None) -> dict[str, Any]:
    try:
        request = HostedInvokeRequest.model_validate(payload)
    except ValidationError as exc:
        raise HostedApiError(HTTPStatus.BAD_REQUEST, exc.json()) from exc

    try:
        result = run_demo_workflow(
            learner_id=request.learner_id,
            request_text=request.request_text,
            selected_lab_id=request.selected_lab_id,
            lab_responses=request.lab_responses,
            demo_response_profile=request.demo_response_profile,
            config=config,
        )
    except ValueError as exc:
        raise HostedApiError(HTTPStatus.BAD_REQUEST, str(exc)) from exc

    return result.model_dump(mode="json")


def create_handler(config: RuntimeConfig | None = None) -> type[BaseHTTPRequestHandler]:
    runtime_config = config

    class HostedAgentHandler(BaseHTTPRequestHandler):
        server_version = "CybersecurityReadinessHostedAgent/1.0"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler naming.
            path = urlparse(self.path).path
            if path != "/health":
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "not_found", "message": "Use GET /health or POST /invoke."},
                )
                return
            self._write_json(HTTPStatus.OK, health_payload(runtime_config))

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler naming.
            path = urlparse(self.path).path
            if path != "/invoke":
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "not_found", "message": "Use GET /health or POST /invoke."},
                )
                return

            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "bad_request", "message": "Invalid Content-Length."},
                )
                return

            try:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(raw_body or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "bad_request", "message": "Request body must be valid JSON."},
                )
                return

            try:
                response_payload = invoke_payload(payload, runtime_config)
            except HostedApiError as exc:
                self._write_json(
                    exc.status,
                    {"error": exc.status.phrase.lower().replace(" ", "_"), "message": exc.message},
                )
                return
            except Exception as exc:  # pragma: no cover - defensive server boundary.
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "internal_server_error", "message": str(exc)},
                )
                return

            self._write_json(HTTPStatus.OK, response_payload)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return HostedAgentHandler


def run_server(host: str = "0.0.0.0", port: int = DEFAULT_HOSTED_AGENT_API_PORT) -> None:
    server = ThreadingHTTPServer((host, port), create_handler())
    print(f"Hosted agent API listening on http://{host}:{port}", flush=True)
    server.serve_forever()


def main() -> None:
    host = environ.get("HOSTED_AGENT_API_HOST", "0.0.0.0")
    raw_port = environ.get("HOSTED_AGENT_API_PORT", str(DEFAULT_HOSTED_AGENT_API_PORT))
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise SystemExit(f"HOSTED_AGENT_API_PORT must be an integer, got {raw_port!r}.") from exc
    run_server(host=host, port=port)


if __name__ == "__main__":
    main()
