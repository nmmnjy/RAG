from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


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
