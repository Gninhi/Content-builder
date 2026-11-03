import os
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from infra.db.models import Base, UserModel, WorkspaceModel


def test_production_skips_hardcoded_seeds():
    """In pure production without dev fixtures flag, lifespan must NOT seed users or ws_default."""
    from apps.api.main import app

    # Create isolated in-memory DB shared across connections using StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with patch.dict(os.environ, {"APP_ENV": "production", "ENABLE_DEV_FIXTURES": "false", "ENABLE_BACKGROUND_DAEMONS": "false"}):
        with patch("apps.api.main.SessionLocal", TestingSessionLocal):
            with TestClient(app):
                pass

    # Verify no default users or workspaces were seeded
    session = TestingSessionLocal()
    try:
        users = session.query(UserModel).all()
        workspaces = session.query(WorkspaceModel).all()
        assert len(users) == 0, f"Expected 0 users seeded in production, found: {[u.id for u in users]}"
        assert len(workspaces) == 0, f"Expected 0 workspaces seeded in production, found: {[w.id for w in workspaces]}"
    finally:
        session.close()


def test_dev_environment_seeds_fixtures():
    """In development or when ENABLE_DEV_FIXTURES is true, lifespan seeds defaults."""
    from apps.api.main import app

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with patch.dict(os.environ, {"APP_ENV": "development", "ENABLE_DEV_FIXTURES": "true", "ENABLE_BACKGROUND_DAEMONS": "false"}):
        with patch("apps.api.main.SessionLocal", TestingSessionLocal):
            with TestClient(app):
                pass

    session = TestingSessionLocal()
    try:
        user_ids = {u.id for u in session.query(UserModel).all()}
        assert "owner_martial" in user_ids
        ws = session.query(WorkspaceModel).filter(WorkspaceModel.id == "ws_default").first()
        assert ws is not None
        assert ws.name == "Default Editorial Workspace"
    finally:
        session.close()
