import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from infra.db.database import Base, SYNC_DATABASE_URL
import infra.db.models  # noqa: F401 - register all tables

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    # First check if custom url is specified on the Alembic Config object (e.g. from tests or CLI)
    config_url = config.get_main_option("sqlalchemy.url")
    ini_default = "sqlite:///./contentops.db"

    # If caller/test explicitly configured a database url different from default ini
    if config_url and config_url not in (ini_default, "driver://user:pass@localhost/dbname"):
        return config_url

    db_env_url = os.getenv("DATABASE_URL")
    if db_env_url:
        if db_env_url.startswith("sqlite+aiosqlite"):
            return db_env_url.replace("sqlite+aiosqlite", "sqlite")
        elif db_env_url.startswith("postgresql+asyncpg"):
            return db_env_url.replace("postgresql+asyncpg", "postgresql")
        return db_env_url

    if config_url and config_url != "driver://user:pass@localhost/dbname":
        return config_url

    return SYNC_DATABASE_URL



def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {}) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True if "sqlite" in get_url() else False
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
