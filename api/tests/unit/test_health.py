from fastapi.testclient import TestClient

from app.main import app


def test_health_ok_and_has_request_id() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert resp.headers["x-request-id"]
