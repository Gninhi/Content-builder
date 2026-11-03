import atexit
import os
import shutil
import tempfile
from pathlib import Path

# Create an isolated temporary directory and SQLite database for the entire pytest session
# so tests NEVER write to or mutate the developer's main contentops.db database.
_TEST_TMP_DIR = tempfile.mkdtemp(prefix="contentops_pytest_")
_TEST_DB_PATH = Path(_TEST_TMP_DIR) / "pytest_contentops.db"


def _cleanup_test_tmp_dir() -> None:
    shutil.rmtree(_TEST_TMP_DIR, ignore_errors=True)


atexit.register(_cleanup_test_tmp_dir)

# Configure global test environment defaults ensuring fail-closed tests pass securely
os.environ["CONTENTOPS_TEST_MODE"] = "1"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("SECRET_VAULT_KEY", "cbe7e00447543d905f45c9b5b702949529b8f356c6ed5c28e0ea21d53ce34536")
os.environ.setdefault("JWT_SECRET_KEY", "f9b2d8e4c1a705e38d9b1c2a4f6e80237d5c9e1b3a5f70248c6e91d3b5a7c2e4")
os.environ.setdefault("SOCIAL_SANDBOX_MODE", "true")
os.environ.setdefault("LIVE_PUBLISHING_ENABLED", "false")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "false")
os.environ.setdefault("ENABLE_BACKGROUND_DAEMONS", "false")
os.environ.setdefault("ENABLE_DEV_FIXTURES", "true")

import pytest  # noqa: E402
from infra.db.database import init_db, SessionLocal  # noqa: E402
from infra.db.repository import ContentOpsRepository  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_db_initialized():
    """Ensure SQLAlchemy tables and default fixtures are initialized in the isolated test DB."""
    init_db()
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        repo.ensure_default_users()
        repo.ensure_workspace("ws_default")
    finally:
        db.close()


