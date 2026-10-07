import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./contentops.db")

# Normalize URL for standard SQLAlchemy if needed
if DATABASE_URL.startswith("sqlite+aiosqlite"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
elif DATABASE_URL.startswith("postgresql+asyncpg"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
else:
    SYNC_DATABASE_URL = DATABASE_URL

engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SYNC_DATABASE_URL else {}
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()


@contextmanager
def get_db_session():
    """Context manager for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db():
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes tables in database and applies backwards-compatible column additions."""
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
    except Exception:
        pass

