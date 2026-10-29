"""reconcile veille_sources, signals, ideas.signal_id, and user_refresh_tokens.revoked_at

Revision ID: 8f3a4b5c6d7e
Revises: 7e2f3a4b5c6d
Create Date: 2026-10-29 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f3a4b5c6d7e"
down_revision: Union[str, Sequence[str], None] = "7e2f3a4b5c6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Create veille_sources table if missing
    if not _has_table(inspector, "veille_sources"):
        op.create_table(
            "veille_sources",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("workspace_id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("url", sa.Text(), nullable=False),
            sa.Column("axis", sa.String(length=64), nullable=False),
            sa.Column("trust_level", sa.String(length=8), nullable=False, server_default="B"),
            sa.Column("source_type", sa.String(length=32), nullable=False, server_default="web"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("health_status", sa.String(length=32), nullable=False, server_default="HEALTHY"),
            sa.Column("last_polled_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_veille_sources_workspace_id", "veille_sources", ["workspace_id"], unique=False)
        op.create_index("ix_veille_sources_axis", "veille_sources", ["axis"], unique=False)

    # 2. Create signals table if missing
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "signals"):
        op.create_table(
            "signals",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("workspace_id", sa.String(length=64), nullable=False),
            sa.Column("source_id", sa.String(length=64), nullable=True),
            sa.Column("canonical_url", sa.Text(), nullable=True),
            sa.Column("url_hash", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=512), nullable=False),
            sa.Column("title_hash", sa.String(length=64), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("axis", sa.String(length=64), nullable=False),
            sa.Column("trust_level", sa.String(length=8), nullable=False, server_default="B"),
            sa.Column("qualification_score", sa.Float(), nullable=False, server_default="3.0"),
            sa.Column("qualification_criteria", sa.JSON(), nullable=False),
            sa.Column("facts", sa.JSON(), nullable=False),
            sa.Column("executive_takeaway", sa.Text(), nullable=False),
            sa.Column("raw_content_ref", sa.Text(), nullable=True),
            sa.Column(
                "enrichment_status",
                sa.String(length=32),
                nullable=False,
                server_default="deterministic_only",
            ),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="QUALIFIED"),
            sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_id"], ["veille_sources.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_signals_workspace_id", "signals", ["workspace_id"], unique=False)
        op.create_index("ix_signals_source_id", "signals", ["source_id"], unique=False)
        op.create_index("ix_signals_url_hash", "signals", ["url_hash"], unique=False)
        op.create_index("ix_signals_title_hash", "signals", ["title_hash"], unique=False)
        op.create_index("ix_signals_axis", "signals", ["axis"], unique=False)
        op.create_index("ix_signals_status", "signals", ["status"], unique=False)
        op.create_index("ix_signals_created_at", "signals", ["created_at"], unique=False)
        op.create_index("ix_signals_workspace_status", "signals", ["workspace_id", "status"], unique=False)
    else:
        if not _has_column(inspector, "signals", "enrichment_status"):
            op.add_column(
                "signals",
                sa.Column(
                    "enrichment_status",
                    sa.String(length=32),
                    nullable=False,
                    server_default="deterministic_only",
                ),
            )

    # 3. Add ideas.signal_id column and index if missing
    inspector = sa.inspect(bind)
    if _has_table(inspector, "ideas"):
        if not _has_column(inspector, "ideas", "signal_id"):
            with op.batch_alter_table("ideas") as batch_op:
                batch_op.add_column(sa.Column("signal_id", sa.String(length=64), nullable=True))
                batch_op.create_index("ix_ideas_signal_id", ["signal_id"], unique=False)
                batch_op.create_foreign_key(
                    "fk_ideas_signal_id_signals",
                    "signals",
                    ["signal_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        elif not _has_index(inspector, "ideas", "ix_ideas_signal_id"):
            op.create_index("ix_ideas_signal_id", "ideas", ["signal_id"], unique=False)

    # 4. Add user_refresh_tokens.revoked_at column if missing
    inspector = sa.inspect(bind)
    if _has_table(inspector, "user_refresh_tokens") and not _has_column(
        inspector, "user_refresh_tokens", "revoked_at"
    ):
        op.add_column(
            "user_refresh_tokens",
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "user_refresh_tokens") and _has_column(
        inspector, "user_refresh_tokens", "revoked_at"
    ):
        with op.batch_alter_table("user_refresh_tokens") as batch_op:
            batch_op.drop_column("revoked_at")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "ideas") and _has_column(inspector, "ideas", "signal_id"):
        with op.batch_alter_table("ideas") as batch_op:
            if _has_index(inspector, "ideas", "ix_ideas_signal_id"):
                batch_op.drop_index("ix_ideas_signal_id")
            batch_op.drop_column("signal_id")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "signals"):
        for idx in (
            "ix_signals_workspace_status",
            "ix_signals_created_at",
            "ix_signals_status",
            "ix_signals_axis",
            "ix_signals_title_hash",
            "ix_signals_url_hash",
            "ix_signals_source_id",
            "ix_signals_workspace_id",
        ):
            if _has_index(inspector, "signals", idx):
                op.drop_index(idx, table_name="signals")
        op.drop_table("signals")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "veille_sources"):
        for idx in ("ix_veille_sources_axis", "ix_veille_sources_workspace_id"):
            if _has_index(inspector, "veille_sources", idx):
                op.drop_index(idx, table_name="veille_sources")
        op.drop_table("veille_sources")

