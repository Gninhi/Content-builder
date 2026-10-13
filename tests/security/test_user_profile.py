import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from apps.api.main import app
from packages.security.auth import create_access_token, Role
from infra.db.database import init_db, SessionLocal
from infra.db.repository import ContentOpsRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment():
    init_db()
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        repo.ensure_default_users()
        if not repo.get_workspace("ws_profile_test"):
            ws = repo.create_workspace("Profile Test WS", owner_id="user_owner_profile")
            ws.id = "ws_profile_test"  # type: ignore[assignment]
            db.commit()
            repo.add_workspace_member("ws_profile_test", "user_owner_profile", "Owner")
            repo.add_workspace_member("ws_profile_test", "user_editor_profile", "Editor")
    finally:
        db.close()


def test_unauthenticated_profile_access_rejected():
    res = client.get("/v1/me")
    assert res.status_code == 401


def test_get_my_profile_returns_workspaces_and_profile():
    token = create_access_token(
        user_id="user_editor_profile",
        role=Role.EDITOR,
        workspace_id="ws_profile_test",
    )
    res = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "user_editor_profile"
    assert "workspaces" in data
    assert any(w["workspace_id"] == "ws_profile_test" for w in data["workspaces"])


def test_update_my_profile_success():
    token = create_access_token(
        user_id="user_editor_profile",
        role=Role.EDITOR,
        workspace_id="ws_profile_test",
    )
    update_payload = {
        "display_name": "Senior Editor",
        "job_title": "Head of Copy",
        "timezone": "Europe/Paris",
        "theme": "light",
        "language": "en",
        "notification_preferences": {"email_alerts": True, "browser_push": False},
        "ui_preferences": {"density": "compact"},
    }
    res = client.patch(
        "/v1/me",
        headers={"Authorization": f"Bearer {token}"},
        json=update_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "Senior Editor"
    assert data["job_title"] == "Head of Copy"
    assert data["timezone"] == "Europe/Paris"
    assert data["theme"] == "light"
    assert data["language"] == "en"
    assert data["notification_preferences"]["email_alerts"] is True
    assert data["ui_preferences"]["density"] == "compact"


def test_mass_assignment_sensitive_fields_forbidden():
    token = create_access_token(
        user_id="user_editor_profile",
        role=Role.EDITOR,
        workspace_id="ws_profile_test",
    )
    # Attempting to tamper with email or role
    res = client.patch(
        "/v1/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "hacked@evil.com"},
    )
    assert res.status_code == 422

    res_role = client.patch(
        "/v1/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "Owner"},
    )
    assert res_role.status_code == 422


def test_invalid_timezone_rejected():
    token = create_access_token(
        user_id="user_editor_profile",
        role=Role.EDITOR,
        workspace_id="ws_profile_test",
    )
    res = client.patch(
        "/v1/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"timezone": "Mars/Olympus_Mons"},
    )
    assert res.status_code == 422
    assert "Fuseau horaire IANA invalide" in res.text


def test_avatar_upload_valid_image():
    token = create_access_token(
        user_id="user_editor_profile",
        role=Role.EDITOR,
        workspace_id="ws_profile_test",
    )
    # Create small valid test PNG in memory
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    res = client.post(
        "/v1/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("avatar.png", buf.getvalue(), "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert "avatar_url" in data
    avatar_url = data["avatar_url"]

    # Verify serving avatar
    get_res = client.get(avatar_url)
    assert get_res.status_code == 200
    assert get_res.headers.get("x-content-type-options") == "nosniff"
    assert "image/webp" in get_res.headers.get("content-type", "")


def test_avatar_upload_rejects_svg_and_malicious():
    token = create_access_token(
        user_id="user_editor_profile",
        role=Role.EDITOR,
        workspace_id="ws_profile_test",
    )
    svg_payload = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert('xss')</script></svg>"
    res = client.post(
        "/v1/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("malicious.svg", svg_payload, "image/svg+xml")},
    )
    assert res.status_code == 415


def test_change_password_and_revokes_other_sessions():
    import uuid
    suffix = uuid.uuid4().hex[:8]
    jti_1 = f"sess_pwd_1_{suffix}"
    jti_2 = f"sess_pwd_2_{suffix}"
    user_id = f"user_pwd_test_{suffix}"

    token_1 = create_access_token(user_id=user_id, role=Role.EDITOR, workspace_id="ws_profile_test", jti=jti_1)
    token_2 = create_access_token(user_id=user_id, role=Role.EDITOR, workspace_id="ws_profile_test", jti=jti_2)

    # Register both sessions in repository
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        repo.get_or_create_user(user_id, default_role="Editor", workspace_id="ws_profile_test")
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        repo.create_session(user_id, jti_1, expires_at=now + timedelta(hours=1))
        repo.create_session(user_id, jti_2, expires_at=now + timedelta(hours=1))
    finally:
        db.close()

    # Weak password attempt
    weak_res = client.post(
        "/v1/me/change-password",
        headers={"Authorization": f"Bearer {token_1}"},
        json={"current_password": "any", "new_password": "weak"},
    )
    assert weak_res.status_code == 422

    # Valid change
    valid_res = client.post(
        "/v1/me/change-password",
        headers={"Authorization": f"Bearer {token_1}"},
        json={"current_password": "any", "new_password": "StrongPassword2026!"},
    )
    assert valid_res.status_code == 200

    # Token 1 (current session) still works
    res_1 = client.get("/v1/me", headers={"Authorization": f"Bearer {token_1}"})
    assert res_1.status_code == 200

    # Token 2 (other session) is revoked
    res_2 = client.get("/v1/me", headers={"Authorization": f"Bearer {token_2}"})
    assert res_2.status_code == 401
    assert "Session révoquée" in res_2.text


def test_sessions_management_and_idor_protection():
    import uuid
    suffix = uuid.uuid4().hex[:8]
    user_a = f"user_sess_a_{suffix}"
    user_b = f"user_sess_b_{suffix}"
    jti_a = f"jti_sess_a_{suffix}"
    jti_b = f"jti_sess_b_{suffix}"

    token_a = create_access_token(user_id=user_a, role=Role.EDITOR, workspace_id="ws_profile_test", jti=jti_a)
    _token_b = create_access_token(user_id=user_b, role=Role.EDITOR, workspace_id="ws_profile_test", jti=jti_b)

    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        repo.get_or_create_user(user_a, default_role="Editor", workspace_id="ws_profile_test")
        repo.get_or_create_user(user_b, default_role="Editor", workspace_id="ws_profile_test")
        from datetime import datetime, timezone, timedelta
        exp = datetime.now(timezone.utc) + timedelta(hours=1)
        sess_a = repo.create_session(user_a, jti_a, exp, user_agent="Mozilla/5.0")
        sess_b = repo.create_session(user_b, jti_b, exp, user_agent="Mozilla/5.0")
        sess_a_id = sess_a.id
        sess_b_id = sess_b.id
    finally:
        db.close()

    # User A lists sessions
    list_res = client.get("/v1/me/sessions", headers={"Authorization": f"Bearer {token_a}"})
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["token_jti"] == jti_a for s in sessions)

    # User A attempts to revoke User B's session (IDOR attack)
    idor_res = client.delete(f"/v1/me/sessions/{sess_b_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert idor_res.status_code == 404

    # User A revokes own session
    own_res = client.delete(f"/v1/me/sessions/{sess_a_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert own_res.status_code == 200


def test_export_my_data_gdpr():
    token = create_access_token(
        user_id="user_editor_profile",
        role=Role.EDITOR,
        workspace_id="ws_profile_test",
    )
    res = client.get("/v1/me/export", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "user" in data
    assert "workspaces" in data
    assert "sessions" in data
    assert "recent_audit_logs" in data
    assert "password_hash" not in data["user"]


def test_delete_account_blocked_if_last_owner():
    token_owner = create_access_token(
        user_id="user_owner_profile",
        role=Role.OWNER,
        workspace_id="ws_profile_test",
    )
    res = client.delete("/v1/me", headers={"Authorization": f"Bearer {token_owner}"})
    assert res.status_code == 400
    assert "unique Propriétaire (Owner)" in res.text


def test_delete_account_anonymizes_non_owner():
    token_editor = create_access_token(
        user_id="user_editor_profile",
        role=Role.EDITOR,
        workspace_id="ws_profile_test",
    )
    res = client.delete("/v1/me", headers={"Authorization": f"Bearer {token_editor}"})
    assert res.status_code == 200
    assert "anonymisées conformément au RGPD" in res.text

    # Verify user record is anonymized and inactive
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        u = repo.get_user("user_editor_profile")
        assert u is not None
        assert u.is_active is False
        assert "anonymized" in str(u.email)
        assert u.full_name == "Compte Supprimé"
    finally:
        db.close()
