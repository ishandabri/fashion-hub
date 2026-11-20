from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_build_info_is_authenticated():
    with TestClient(app) as client:
        assert client.get("/api/v1/system/build").status_code == 401
        login = client.post("/api/v1/auth/login", json={"username": "test-owner", "password": "test-password"})
        assert login.status_code == 200
        response = client.get("/api/v1/system/build")
    assert response.status_code == 200
    assert set(response.json()) == {"version", "revision", "built_at"}


def test_client_event_is_authenticated_and_logged(caplog):
    with TestClient(app) as client:
        assert client.post("/api/v1/system/client-events", json={"event_type": "PWA_UPDATE_CHECK_FAILED", "frontend_version": "0.1.0", "frontend_revision": "abc123", "message": "network failure"}).status_code == 401
        login = client.post("/api/v1/auth/login", json={"username": "test-owner", "password": "test-password"})
        assert login.status_code == 200
        response = client.post("/api/v1/system/client-events", json={"event_type": "PWA_UPDATE_CHECK_FAILED", "frontend_version": "0.1.0", "frontend_revision": "abc123", "message": "network\n failure"})
    assert response.status_code == 204
    assert "PWA_UPDATE_CHECK_FAILED" in caplog.text
    assert "network failure" in caplog.text


def test_client_event_rejects_unknown_event_type():
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "test-owner", "password": "test-password"})
        response = client.post("/api/v1/system/client-events", json={"event_type": "UNKNOWN", "frontend_version": "0.1.0", "frontend_revision": "abc123", "message": "bad"})
    assert response.status_code == 422

