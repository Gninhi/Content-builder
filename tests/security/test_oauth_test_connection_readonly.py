from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from packages.security.auth import create_access_token
from packages.connectors.social.base import SocialPublisher

client = TestClient(app, raise_server_exceptions=False)


def test_oauth_test_connection_never_calls_publish():
    """C6: /oauth/test-connection/{provider} must be strictly read-only and never call publish()."""
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("OAuth Test WS", "UTC", "owner_oauth")
        db.commit()

        owner_token = create_access_token(user_id="owner_oauth", role="Owner", workspace_id=ws.id)

    mock_publisher = MagicMock(spec=SocialPublisher)
    mock_publisher.verify_connection.return_value = {
        "status": "OPERATIONAL",
        "provider": "linkedin",
        "account_id": "urn:li:person:test_123",
        "mode": "read_only_test"
    }

    with patch("services.publisher.worker.PublisherWorker.resolve_publisher", return_value=mock_publisher):
        res = client.post(
            "/v1/oauth/test-connection/linkedin",
            headers={"Authorization": f"Bearer {owner_token}"}
        )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert data["provider"] == "linkedin"

    # CRITICAL SECURITY CHECK: publish() must NEVER be invoked!
    mock_publisher.publish.assert_not_called()
    mock_publisher.verify_connection.assert_called_once()
