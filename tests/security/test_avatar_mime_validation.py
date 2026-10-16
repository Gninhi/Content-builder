import io
import os
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.dependencies import get_current_user, UserContext, get_repository, get_db
from infra.db.repository import ContentOpsRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import infra.db.models
from infra.db.models import Base, UserModel


@pytest.fixture
def auth_client(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Pre-seed test user
    db = TestingSession()
    repo = ContentOpsRepository(db)
    repo.create_workspace(name="Test Workspace", workspace_id="ws_test", owner_id="user_avatar_tester")
    repo.create_user(
        user_id="user_avatar_tester",
        email="avatar@test.com",
        password_hash="fakehash",
        full_name="Avatar Tester",
    )
    db.close()

    test_user = UserContext(user_id="user_avatar_tester", role="Owner", workspace_id="ws_test")

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    def override_get_repository():
        session = TestingSession()
        try:
            yield ContentOpsRepository(session)
        finally:
            session.close()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_repository] = override_get_repository

    with TestClient(app) as client:
        yield client, TestingSession

    app.dependency_overrides.clear()


def test_reject_executable_disguised_as_png(auth_client):
    client, _ = auth_client
    # PE executable header (MZ...) masquerading as avatar.png
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This program cannot be run in DOS mode."
    files = {"file": ("malicious.png", fake_exe, "image/png")}

    response = client.post("/v1/me/avatar", files=files)
    assert response.status_code == 415
    assert "Format d'image non supporté" in response.json()["detail"]


def test_reject_svg_disguised_as_jpeg(auth_client):
    client, _ = auth_client
    svg_payload = b"<svg xmlns=\"http://www.w3.org/2000/svg\"><script>alert('xss')</script></svg>"
    files = {"file": ("avatar.jpg", svg_payload, "image/jpeg")}

    response = client.post("/v1/me/avatar", files=files)
    assert response.status_code == 415
    assert "SVG sont strictement interdits" in response.json()["detail"]


def test_reject_html_disguised_as_webp(auth_client):
    client, _ = auth_client
    html_payload = b"<!DOCTYPE html><html><body><script>malware()</script></body></html>"
    files = {"file": ("avatar.webp", html_payload, "image/webp")}

    response = client.post("/v1/me/avatar", files=files)
    assert response.status_code == 415


def test_reject_avatar_exceeding_size_limit(auth_client):
    client, _ = auth_client
    # 2MB + 10 bytes
    oversized = b"\xff\xd8\xff\xe0" + b"\x00" * (2 * 1024 * 1024 + 10)
    files = {"file": ("oversized.jpg", oversized, "image/jpeg")}

    response = client.post("/v1/me/avatar", files=files)
    assert response.status_code == 413
    assert "dépasse la limite autorisée" in response.json()["detail"] or "dépasse la taille maximale autorisée" in response.json()["detail"]


def test_reject_corrupted_image_with_fake_magic_bytes(auth_client):
    client, _ = auth_client
    # Starts with PNG magic bytes but followed by garbage
    corrupt_png = b"\x89PNG\r\n\x1a\n" + b"CORRUPTED_GARBAGE_PAYLOAD_NOT_IMAGE"
    files = {"file": ("corrupt.png", corrupt_png, "image/png")}

    response = client.post("/v1/me/avatar", files=files)
    assert response.status_code == 400
    assert "Le fichier fourni n'est pas une image valide" in response.json()["detail"]


def test_accept_valid_png_and_normalize_to_webp(auth_client):
    client, session_factory = auth_client
    # Create legitimate PNG image using Pillow
    img = Image.new("RGB", (200, 200), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    files = {"file": ("valid.png", buf.getvalue(), "image/png")}
    response = client.post("/v1/me/avatar", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "avatar_url" in data
    assert data["avatar_url"].endswith(".webp")

    # Verify user profile was updated in DB
    db = session_factory()
    try:
        user = db.query(UserModel).filter(UserModel.id == "user_avatar_tester").first()
        assert user is not None
        assert user.avatar_url == data["avatar_url"]
    finally:
        db.close()


def test_accept_valid_jpeg(auth_client):
    client, session_factory = auth_client
    img = Image.new("RGB", (150, 150), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"file": ("valid.jpg", buf.getvalue(), "image/jpeg")}
    response = client.post("/v1/me/avatar", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"].startswith("/v1/avatars/avatar_user_avatar_tester_")
    assert data["avatar_url"].endswith(".webp")
