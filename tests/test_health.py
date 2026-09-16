from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_health_reports_environment():
    body = client.get("/health").json()

    assert body["environment"] == "development"
    assert "git_sha" in body
