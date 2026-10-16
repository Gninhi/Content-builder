import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

import infra.db.models
from infra.db.models import Base, WorkspaceModel
from infra.db.repository import ContentOpsRepository, NotFoundError, WorkspaceNotFoundError


@pytest.fixture
def test_repo():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    repo = ContentOpsRepository(session)
    yield repo, session
    session.close()


def test_ensure_workspace_raises_not_found_on_missing_id(test_repo):
    repo, session = test_repo
    non_existent_id = "ws_does_not_exist_12345"

    with pytest.raises(NotFoundError) as exc_info:
        repo.ensure_workspace(non_existent_id)

    assert non_existent_id in str(exc_info.value)

    # Ensure NO phantom workspace was created in database
    ws_in_db = session.query(WorkspaceModel).filter(WorkspaceModel.id == non_existent_id).first()
    assert ws_in_db is None
    assert session.query(WorkspaceModel).count() == 0


def test_ensure_workspace_returns_existing_workspace(test_repo):
    repo, session = test_repo
    created_ws = repo.create_workspace(name="Legitimate Workspace", workspace_id="ws_legit_1")

    retrieved = repo.ensure_workspace("ws_legit_1")
    assert retrieved is not None
    assert retrieved.id == "ws_legit_1"
    assert retrieved.name == "Legitimate Workspace"


def test_repository_methods_fail_closed_on_missing_workspace(test_repo):
    repo, session = test_repo
    bad_id = "ws_phantom_ghost"

    with pytest.raises(NotFoundError):
        repo.add_source(
            workspace_id=bad_id,
            source_type="url",
            canonical_url="https://example.com",
            raw_content_ref="ref",
            extracted_facts=[],
            provenance={}
        )

    with pytest.raises(NotFoundError):
        repo.create_or_version_brand_profile(
            workspace_id=bad_id,
            audience=["Engineers"],
            voice="Formal",
            pillars=["Architecture"],
            prohibited_topics=[],
            cta_policy={}
        )

    assert session.query(WorkspaceModel).filter(WorkspaceModel.id == bad_id).first() is None


def test_fastapi_handles_not_found_error_with_404():
    """Ensure FastAPI translates repository NotFoundError into an HTTP 404 response."""
    from apps.api.main import app

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    from apps.api.dependencies import get_db, get_repository, UserContext, require_roles

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_repository():
        db = TestingSessionLocal()
        try:
            yield ContentOpsRepository(db)
        finally:
            db.close()

    # Authenticated user pointing to a missing workspace
    ghost_user = UserContext(user_id="user_test", role="Owner", workspace_id="ws_missing_phantom")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_repository] = override_get_repository
    # Override role requirement for testing
    from apps.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: ghost_user

    try:
        client = TestClient(app)
        # Attempt to ingest source with non-existent workspace in context
        response = client.post(
            "/v1/sources",
            json={
                "workspace_id": "ws_missing_phantom",
                "type": "url",
                "url": "https://example.com/test",
                "raw_text": "sample content"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
