from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_spa_fallback_routes():
    # Primary UI entrypoint
    resp_ui = client.get("/ui")
    assert resp_ui.status_code == 200
    assert "<html" in resp_ui.text.lower()

    # Direct deep-link HTML5 subroutes without hash
    for subroute in ["/ui/dashboard", "/ui/veille", "/ui/inbox", "/ui/connections"]:
        resp = client.get(subroute)
        assert resp.status_code == 200
        assert "<html" in resp.text.lower()
        # Verify it served the SPA index.html
        assert "ContentOps" in resp.text or "root" in resp.text

