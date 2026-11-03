import os
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Prioritize values from .env file in normal execution, but never overwrite explicit test environment variables
_is_test_mode = (
    os.environ.get("CONTENTOPS_TEST_MODE") == "1"
    or "PYTEST_CURRENT_TEST" in os.environ
    or os.environ.get("APP_ENV") in ("test", "testing")
)
load_dotenv(find_dotenv(usecwd=True), override=not _is_test_mode)


def resolve_database_url(raw_url: str) -> str:
    """
    Normalizes DATABASE_URL and stabilizes relative SQLite paths against PROJECT_ROOT
    so starting Uvicorn from any working directory always targets the same database file.
    """
    url = (raw_url or "sqlite:///./contentops.db").strip()
    if url.startswith("sqlite+aiosqlite"):
        url = url.replace("sqlite+aiosqlite", "sqlite", 1)
    elif url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if url.startswith("sqlite:///") and url != "sqlite:///:memory:" and not url.startswith("sqlite:///:memory:"):
        raw_path = url[len("sqlite:///"):]
        # Separate optional URI query parameters if any
        path_part, sep, query_part = raw_path.partition("?")
        if path_part.startswith("./"):
            path_part = path_part[2:]
        p = Path(path_part)
        if not p.is_absolute():
            p = (PROJECT_ROOT / p).resolve()
        resolved = f"sqlite:///{p}"
        if sep:
            resolved = f"{resolved}?{query_part}"
        return resolved
    return url


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./contentops.db")
SYNC_DATABASE_URL = resolve_database_url(DATABASE_URL)

engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SYNC_DATABASE_URL else {}
)


@event.listens_for(engine, "connect")
def _configure_sqlite_connection(dbapi_connection, connection_record) -> None:
    """Enforces foreign keys, busy timeout, and WAL mode on every SQLite connection."""
    if "sqlite" not in SYNC_DATABASE_URL:
        return
    enforce_fk = os.getenv("SQLITE_ENFORCE_FOREIGN_KEYS", "true").strip().lower() in ("true", "1", "yes")
    enable_wal = os.getenv("SQLITE_ENABLE_WAL", "true").strip().lower() in ("true", "1", "yes")
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA busy_timeout = 30000")
        if enforce_fk:
            cursor.execute("PRAGMA foreign_keys = ON")
        if enable_wal and ":memory:" not in SYNC_DATABASE_URL:
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
    except Exception:
        pass
    finally:
        cursor.close()


session_factory = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
SessionLocal = scoped_session(session_factory)

Base = declarative_base()


@contextmanager
def get_db_session():
    """Context manager for obtaining an isolated database session with guaranteed closure."""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_db():
    """Dependency for obtaining an isolated database session per request."""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def set_db_workspace_context(db, workspace_id: str) -> None:
    """
    Binds the active workspace_id to the SQLAlchemy session and, on PostgreSQL,
    sets the transaction-local variable `app.current_workspace_id` used by RLS policies.
    """
    if not workspace_id or db is None:
        return
    try:
        db.info["workspace_id"] = str(workspace_id)
        bind = db.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            from sqlalchemy import text
            db.execute(
                text("SELECT set_config('app.current_workspace_id', :ws_id, true)"),
                {"ws_id": str(workspace_id)},
            )
    except Exception:
        pass


def init_db():
    """Initializes tables in database and applies backwards-compatible column additions."""
    import infra.db.models  # noqa: F401 - Ensure all model tables are registered on Base.metadata
    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        if "content_variants" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("content_variants")]
            if "degraded" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE content_variants ADD COLUMN degraded BOOLEAN DEFAULT 0"))
        if "workspaces" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("workspaces")]
            if "kill_switch_enabled" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE workspaces ADD COLUMN kill_switch_enabled BOOLEAN DEFAULT 0"))
        if "ideas" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("ideas")]
            if "signal_id" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE ideas ADD COLUMN signal_id VARCHAR(64)"))
        if "signals" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("signals")]
            if "enrichment_status" not in columns:
                with engine.begin() as conn:
                    conn.execute(
                        text("ALTER TABLE signals ADD COLUMN enrichment_status VARCHAR(32) DEFAULT 'deterministic_only'")
                    )
        if "user_refresh_tokens" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("user_refresh_tokens")]
            if "revoked_at" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE user_refresh_tokens ADD COLUMN revoked_at DATETIME"))
    except Exception:
        pass

