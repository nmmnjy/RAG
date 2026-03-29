import base64
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import create_app
import app.parsers.registry as parser_registry_module
import app.services.document_parse_service as document_parse_service_module


client = TestClient(create_app())
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "01_document_parsing"


def test_create_and_run_parse_task() -> None:
    create_resp = client.post(
        "/api/v1/document-parse/tasks",
        json={
            "doc_id": "doc_001",
            "kb_id": "kb_001",
            "source": "upload",
            "format": "pdf",
            "version": "v1",
        },
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]
    run_resp = client.post(f"/api/v1/document-parse/tasks/{task_id}/run")
    assert run_resp.status_code == 200
    assert run_resp.json()["data"]["status"] == "succeeded"


def test_get_missing_task() -> None:
    response = client.get("/api/v1/document-parse/tasks/task_not_exists")
    assert response.status_code == 404
    assert response.json()["code"] == "DOC_NOT_FOUND"


def test_create_task_invalid_body_returns_common_invalid_argument() -> None:
    response = client.post(
        "/api/v1/document-parse/tasks",
        json={
            "doc_id": "doc_002",
            "kb_id": "kb_001",
            "source": "upload",
            "format": "invalid_format",
            "version": "v1",
        },
    )
    body = response.json()
    assert response.status_code == 400
    assert body["code"] == "COMMON_INVALID_ARGUMENT"
    assert "message" in body
    assert "details" in body
    assert "request_id" in body
    assert "trace_id" in body


def test_ingest_should_parse_three_sample_formats_successfully() -> None:
    samples = [
        ("pdf", "sample_minimal.pdf", "pdf"),
        ("markdown", "sample_kb_note.md", "markdown"),
        ("txt", "sample_runbook.txt", "txt"),
    ]
    for doc_type, file_name, fmt in samples:
        sample_file = FIXTURE_ROOT / doc_type / file_name
        response = client.post(
            "/api/v1/document-parse/ingest",
            json={
                "doc_id": f"doc_ingest_{fmt}",
                "kb_id": "kb_ingest",
                "filename": file_name,
                "version": "v1",
                "file_content_base64": base64.b64encode(sample_file.read_bytes()).decode("ascii"),
            },
        )
        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "succeeded"
        assert body["format"] == fmt
        structured = body["structured_document"]
        for required_key in ["doc_id", "kb_id", "source", "format", "version", "status"]:
            assert required_key in structured


def test_ingest_should_fail_for_empty_payload() -> None:
    response = client.post(
        "/api/v1/document-parse/ingest",
        json={
            "doc_id": "doc_bad_payload",
            "kb_id": "kb_ingest",
            "filename": "sample.txt",
            "version": "v1",
            "file_content_base64": "",
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "DOC_SOURCE_INVALID"


def test_retry_should_work_for_retryable_task(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        parser_registry_module,
        "settings",
        SimpleNamespace(
            doc_parse_provider="real",
            doc_parse_real_formats={"markdown", "txt"},
            doc_parse_enable_fallback=False,
        ),
    )
    monkeypatch.setattr(
        document_parse_service_module,
        "settings",
        SimpleNamespace(
            parse_max_retry=3,
            doc_parse_provider="real",
            doc_parse_upload_dir="backend/data/uploads",
        ),
    )
    create_resp = client.post(
        "/api/v1/document-parse/tasks",
        json={
            "doc_id": "doc_retry_001",
            "kb_id": "kb_retry",
            "source": "file://not_exists.md",
            "format": "markdown",
            "version": "v1",
        },
    )
    task_id = create_resp.json()["data"]["task_id"]
    first_run = client.post(f"/api/v1/document-parse/tasks/{task_id}/run")
    assert first_run.status_code == 200
    assert first_run.json()["data"]["status"] == "retryable"
    assert first_run.json()["data"]["error_code"] == "DOC_SOURCE_NOT_FOUND"
    retry_run = client.post(f"/api/v1/document-parse/tasks/{task_id}/retry")
    assert retry_run.status_code == 200
    assert retry_run.json()["data"]["retry_count"] == 2


def test_parse_error_mapping_endpoint() -> None:
    response = client.get("/api/v1/document-parse/errors")
    assert response.status_code == 200
    mapping = response.json()["data"]
    assert mapping["DOC_SOURCE_NOT_FOUND"] == 404
    assert mapping["DOC_UNSUPPORTED_FORMAT"] == 400
