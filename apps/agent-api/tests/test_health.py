from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "cineyield-agent-api"
    assert "version" in data


def test_health_includes_correlation_id():
    response = client.get("/health", headers={"X-Correlation-ID": "test-123"})
    assert response.headers.get("X-Correlation-ID") == "test-123"


def test_health_generates_correlation_id_when_absent():
    response = client.get("/health")
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) > 0


def test_ready_returns_ok():
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "checks" in data
    assert data["checks"]["api"] == "ok"


def test_ready_checks_have_valid_values():
    response = client.get("/ready")
    data = response.json()
    # Each service check returns one of: ok, error, not_configured, configured
    valid = {"ok", "error", "not_configured", "configured"}
    assert data["checks"]["gemini"] in valid
    assert data["checks"]["clickhouse"] in valid
    assert data["checks"]["gcs"] in valid
