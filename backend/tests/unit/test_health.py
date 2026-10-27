from fastapi.testclient import TestClient

from forgeai.main import app

client = TestClient(app)


def test_root_returns_application_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "ForgeAI", "version": "0.1.0"}


def test_liveness_endpoint() -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
