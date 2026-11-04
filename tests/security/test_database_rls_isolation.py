"""
Test PostgreSQL RLS workspace isolation and fail-closed security context enforcement (ANOM-07 / ANOM-08).
"""
import pytest
from unittest.mock import MagicMock
from infra.db.database import set_db_workspace_context
from packages.security.exceptions import SecurityContextError


def test_set_db_workspace_context_sqlite():
    """Verify set_db_workspace_context populates session info on SQLite without executing set_config."""
    mock_db = MagicMock()
    mock_db.info = {}
    mock_bind = MagicMock()
    mock_bind.dialect.name = "sqlite"
    mock_db.get_bind.return_value = mock_bind

    set_db_workspace_context(mock_db, "ws_sqlite_123")

    assert mock_db.info["workspace_id"] == "ws_sqlite_123"
    mock_db.execute.assert_not_called()


def test_set_db_workspace_context_postgresql_success():
    """Verify set_db_workspace_context executes set_config on PostgreSQL dialect."""
    mock_db = MagicMock()
    mock_db.info = {}
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_db.get_bind.return_value = mock_bind

    set_db_workspace_context(mock_db, "ws_pg_456")

    assert mock_db.info["workspace_id"] == "ws_pg_456"
    assert mock_db.execute.called
    call_args = mock_db.execute.call_args
    # First argument is SQL text, second is params dict
    assert call_args[0][1] == {"ws_id": "ws_pg_456"}


def test_set_db_workspace_context_postgresql_fail_closed_raises():
    """Verify fail-closed security policy: if set_config fails on PostgreSQL, SecurityContextError is raised."""
    mock_db = MagicMock()
    mock_db.info = {}
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_db.get_bind.return_value = mock_bind
    mock_db.execute.side_effect = RuntimeError("Postgres connection dropped during RLS config")

    with pytest.raises(SecurityContextError) as exc_info:
        set_db_workspace_context(mock_db, "ws_pg_fail")

    assert "Fail-closed tenant isolation failure" in str(exc_info.value)
    assert "ws_pg_fail" in str(exc_info.value)


def test_set_db_workspace_context_empty_or_none_safe():
    """Verify None or empty workspace_id is safely ignored without errors."""
    mock_db = MagicMock()
    mock_db.info = {}

    set_db_workspace_context(mock_db, "")
    assert "workspace_id" not in mock_db.info

    set_db_workspace_context(None, "ws_test")
