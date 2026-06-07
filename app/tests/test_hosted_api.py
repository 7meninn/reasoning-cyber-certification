import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from cybersecurity_readiness.config import load_runtime_config
from cybersecurity_readiness.hosted_api import create_handler, health_payload, invoke_payload


def test_health_payload_reports_mock_status_without_live_config():
    payload = health_payload(load_runtime_config({}))

    assert payload["status"] == "ok"
    assert payload["requested_mode"] == "mock"
    assert payload["effective_mode"] == "mock"
    assert payload["retrieval_mode"] == "local_mock"
    assert payload["live_config_ready"] is False
    assert payload["auth"] == "DefaultAzureCredential"


def test_health_payload_reports_foundry_iq_live_config_ready():
    payload = health_payload(
        load_runtime_config(
            {
                "APP_MODE": "foundry_iq",
                "AZURE_AI_PROJECT_ENDPOINT": "https://demo.services.ai.azure.com/api/projects/readiness",
                "AZURE_AI_MODEL_DEPLOYMENT": "gpt-4o-mini",
                "AZURE_AI_SEARCH_ENDPOINT": "https://demo.search.windows.net",
                "FOUNDRY_IQ_KNOWLEDGE_BASE": "soc-readiness-kb",
            }
        )
    )

    assert payload["requested_mode"] == "foundry_iq"
    assert payload["effective_mode"] == "foundry_iq"
    assert payload["retrieval_mode"] == "foundry_iq"
    assert payload["live_config_ready"] is True


def test_invoke_payload_runs_mock_workflow():
    payload = invoke_payload({}, load_runtime_config({}))

    assert payload["learner"]["learner_id"] == "L-1001"
    assert payload["route"]["route"] == "soc_readiness_demo"
    assert payload["trace"]["effective_app_mode"] == "mock"
    assert payload["assessment_result"]["overall_readiness"] == "CONDITIONAL"


def test_invoke_payload_rejects_invalid_lab_response_shape():
    with pytest.raises(Exception) as exc_info:
        invoke_payload(
            {
                "lab_responses": [
                    {
                        "question_id": "LAB-Q1",
                        "selected_option_ids": "not-a-list",
                    }
                ]
            },
            load_runtime_config({}),
        )

    assert "selected_option_ids" in str(exc_info.value)


def test_hosted_api_http_health_and_invoke():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        create_handler(load_runtime_config({})),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        connection = HTTPConnection("127.0.0.1", port, timeout=10)
        connection.request("GET", "/health")
        health_response = connection.getresponse()
        health_body = json.loads(health_response.read().decode("utf-8"))

        assert health_response.status == 200
        assert health_body["effective_mode"] == "mock"

        connection.request(
            "POST",
            "/invoke",
            body=json.dumps({"learner_id": "L-1001"}),
            headers={"Content-Type": "application/json"},
        )
        invoke_response = connection.getresponse()
        invoke_body = json.loads(invoke_response.read().decode("utf-8"))

        assert invoke_response.status == 200
        assert invoke_body["trace"]["route"] == "soc_readiness_demo"
        assert invoke_body["trace"]["retrieval_mode"] == "local_mock"
    finally:
        server.shutdown()
        server.server_close()
