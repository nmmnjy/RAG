from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.parsers.registry import parser_registry
from app.schemas.document_parse import DocumentFormat, StructuredDocument


client = TestClient(create_app())


def _load_answerable_case() -> dict:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "07_answerable_qa"
        / "qa_answerable_case_v1.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _prepare_succeeded_parse_task_from_case(case: dict) -> None:
    create_resp = client.post(
        "/api/v1/document-parse/tasks",
        json={
            "doc_id": case["doc_id"],
            "kb_id": case["kb_id"],
            "source": case["source"],
            "format": case["format"],
            "version": case["version"],
        },
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    adapter = parser_registry.get(DocumentFormat(case["format"]))
    structured_document = StructuredDocument(**case["structured_document"])
    with patch.object(adapter, "parse", return_value=structured_document):
        run_resp = client.post(f"/api/v1/document-parse/tasks/{task_id}/run")
    assert run_resp.status_code == 200
    assert run_resp.json()["data"]["status"] == "succeeded"


def test_qa_answer_api_should_answer_on_demo_answerable_case() -> None:
    case = _load_answerable_case()
    _prepare_succeeded_parse_task_from_case(case)

    response = client.post(
        "/api/v1/qa/answers",
        json={
            "kb_id": case["kb_id"],
            "doc_id": case["doc_id"],
            "query_text": case["query_text"],
            "top_k": 3,
            "vector_top_k": 6,
            "keyword_top_k": 6,
            "min_score_threshold": 0.0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "OK"
    assert payload["message"] == "success"
    assert "request_id" in payload
    assert "trace_id" in payload
    assert "ts" in payload

    data = payload["data"]
    assert "answer" in data
    assert "citations" in data
    assert "confidence" in data
    assert "refuse_reason" in data
    assert isinstance(data["citations"], list)
    assert data["answer"]
    assert data["citations"]
    assert data["confidence"] > case["expect"]["min_confidence"]
    assert data["refuse_reason"] is None
    assert case["evidence_text"] in data["citations"][0]["snippet"]
    if case["expect"]["answer_should_contain_evidence_text"]:
        assert case["evidence_text"] in data["answer"]


def test_qa_answer_api_should_refuse_when_no_retrieval_context() -> None:
    response = client.post(
        "/api/v1/qa/answers",
        json={
            "kb_id": "kb_qa_empty_001",
            "query_text": "any question",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "OK"
    assert payload["data"]["refuse_reason"] == "QA_CONTEXT_EMPTY"
    assert payload["data"]["citations"] == []
