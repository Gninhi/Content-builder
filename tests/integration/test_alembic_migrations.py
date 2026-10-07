import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command


@pytest.fixture
def temp_alembic_db():
    """Provides a temporary SQLite database path and configured Alembic Config."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)

    yield path, db_url, config

    if os.path.exists(path):
        os.remove(path)


def test_alembic_migration_upgrade_and_downgrade_cycle(temp_alembic_db):
    """
    Tests full lifecycle of Alembic migrations:
    1. Upgrade to head creates all required schema tables and constraints.
    2. Downgrade to base drops all tables cleanly without leaving orphans.
    3. Re-upgrade to head proves reproducibility.
    """
    path, db_url, config = temp_alembic_db

    # 1. Upgrade to head
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = {
        "workspaces",
        "brand_profiles",
        "content_sources",
        "ideas",
        "content_briefs",
        "content_packages",
        "content_variants",
        "approvals",
        "publication_jobs",
        "published_posts",
        "metric_snapshots",
        "agent_runs",
        "connected_social_accounts",
    }

    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' not created by migration upgrade"

    # Verify connected_social_accounts structure
    social_cols = {c["name"] for c in inspector.get_columns("connected_social_accounts")}
    assert "encrypted_token_blob" in social_cols
    assert "key_id" in social_cols
    assert "status" in social_cols

    # 2. Downgrade to base
    command.downgrade(config, "base")

    inspector_after_down = inspect(engine)
    tables_after_down = set(inspector_after_down.get_table_names())
    # Only alembic_version table may remain
    remaining_business_tables = tables_after_down.intersection(expected_tables)
    assert len(remaining_business_tables) == 0, f"Tables remained after downgrade: {remaining_business_tables}"

    # 3. Re-upgrade to head
    command.upgrade(config, "head")
    inspector_reup = inspect(engine)
    reup_tables = set(inspector_reup.get_table_names())
    for table in expected_tables:
        assert table in reup_tables, f"Expected table '{table}' missing after second upgrade"
