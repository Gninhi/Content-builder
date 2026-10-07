from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_liveness_endpoint_health():
    """Verifies that /health returns 200 OK and basic system metadata."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "engine" in data


def test_readiness_endpoint_ready():
    """Verifies that /ready checks database, checkpointer, and LLM key."""
    res = client.get("/ready")
    assert res.status_code in [200, 503]
    data = res.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "checkpointer" in data["checks"]
    assert "llm_key" in data["checks"]
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["checkpointer"] == "ok"
