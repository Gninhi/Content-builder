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


@pytest.fixture(autouse=True)
def mock_nvidia_discovery(monkeypatch):
    """Intercepte les requêtes sortantes de découverte de modèles NVIDIA dans l'environnement de test (ANOM-41)."""
    from services.orchestration.providers.nvidia import NVIDIAProviderAdapter
    from packages.contracts.llm import LLMModelInfo

    def _mock_discover(self):
        return [
            LLMModelInfo(
                provider_id="nvidia",
                model_id="nvidia/llama-3.1-nemotron-70b-instruct",
                display_name="Llama 3.1 Nemotron 70b Instruct",
                capabilities={"text_generation": True, "structured_output": True, "streaming": True},
                parameters={"temperature": {"min": 0.0, "max": 1.0, "default": 0.2}},
                provenance="mocked_discovery",
                is_available=True,
            ),
            LLMModelInfo(
                provider_id="nvidia",
                model_id="z-ai/glm-5.3-flash",
                display_name="Glm 5.3 Flash",
                capabilities={"text_generation": True, "structured_output": True, "streaming": True},
                parameters={"temperature": {"min": 0.0, "max": 1.0, "default": 0.2}},
                provenance="mocked_discovery",
                is_available=True,
            ),
        ]

    monkeypatch.setattr(NVIDIAProviderAdapter, "_discover_remote_models", _mock_discover)

    try:
        from langchain_nvidia_ai_endpoints._common import _NVIDIABaseClient, Model

        mock_models = [
            Model(id="nvidia/llama-3.1-nemotron-70b-instruct", model_type="chat", client="ChatNVIDIA"),
            Model(id="z-ai/glm-5.3-flash", model_type="chat", client="ChatNVIDIA"),
        ]
        monkeypatch.setattr(_NVIDIABaseClient, "available_models", property(lambda self: mock_models))
    except (ImportError, AttributeError):
        pass



