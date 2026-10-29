import os
from contextlib import contextmanager
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# Prioritize values from .env file unconditionally over inherited shell values
load_dotenv(find_dotenv(usecwd=True), override=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./contentops.db")

# Normalize URL for standard SQLAlchemy if needed
if DATABASE_URL.startswith("sqlite+aiosqlite"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
elif DATABASE_URL.startswith("postgresql+asyncpg"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
elif DATABASE_URL.startswith("postgresql://"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
else:
    SYNC_DATABASE_URL = DATABASE_URL

engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SYNC_DATABASE_URL else {}
)

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

