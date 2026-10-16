import uuid
import os
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import utc_now
from datetime import timedelta

client = TestClient(app, raise_server_exceptions=False)


def test_register_response_does_not_leak_account_existence():
    """
    Test H3:
    POST /v1/auth/register MUST return the same keys/format whether the email exists or not.
    Leaking 'user_id' or 'workspace_id' only on new accounts allows account enumeration.
    """
    uid = uuid.uuid4().hex[:8]
    email1 = f"user1_{uid}@company.com"
    payload1 = {
        "email": email1,
        "password": "StrongPassword2026!#",
        "full_name": "User One",
        "cgu_accepted": True,
        "privacy_accepted": True,
    }

    # First registration
    res1 = client.post("/v1/auth/register", json=payload1)
    assert res1.status_code == 201, res1.text
    keys1 = set(res1.json().keys())

    # Second registration with identical email
    res2 = client.post("/v1/auth/register", json=payload1)
    assert res2.status_code == 201, res2.text
    keys2 = set(res2.json().keys())

    assert "user_id" not in keys1, "Vulnerability H3: user_id leaked in register response allowing enumeration"
    assert "workspace_id" not in keys1, "Vulnerability H3: workspace_id leaked in register response allowing enumeration"
    assert keys1 == keys2, f"Register response keys differ! {keys1} vs {keys2}"


def test_locked_account_returns_401_not_423_to_prevent_enumeration():
    """
    Test H3:
    When an account is locked due to failed attempts, login MUST return 401 (not 423).
    Returning 423 confirms the email exists and allows account enumeration.
    """
    uid = uuid.uuid4().hex[:8]
    email = f"locked_{uid}@company.com"
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        u = repo.create_user(user_id=f"usr_{uid}", email=email, full_name="Locked User", password_hash="dummy")
        u.locked_until = utc_now() + timedelta(minutes=15)
        db.commit()

    res = client.post("/v1/auth/login", json={"email": email, "password": "AnyPassword123!"})
    assert res.status_code == 401, f"Expected 401, but got {res.status_code} (status 423 leaks account existence!)"


def test_demo_mode_is_disabled_by_default():
    """
    Test H7:
    DEMO_MODE_ENABLED must default to false (not true).
    POST /v1/auth/demo must return 404 when DEMO_MODE_ENABLED is not explicitly set to 'true'.
    """
    old = os.environ.pop("DEMO_MODE_ENABLED", None)
    try:
        res = client.post("/v1/auth/demo")
        assert res.status_code == 404, f"Vulnerability H7: Demo mode is enabled by default! Got {res.status_code}"
    finally:
        if old is not None:
            os.environ["DEMO_MODE_ENABLED"] = old
