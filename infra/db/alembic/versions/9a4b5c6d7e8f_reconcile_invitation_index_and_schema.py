"""reconcile workspace_invitations index name and schema constraints

Revision ID: 9a4b5c6d7e8f
Revises: 8f3a4b5c6d7e
Create Date: 2026-10-29 20:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a4b5c6d7e8f"
down_revision: Union[str, Sequence[str], None] = "8f3a4b5c6d7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "workspace_invitations"):
        if _has_index(inspector, "workspace_invitations", "ix_workspace_invitations_code_hash"):
            op.drop_index("ix_workspace_invitations_code_hash", table_name="workspace_invitations")
        inspector = sa.inspect(bind)
        if not _has_index(
            inspector,
            "workspace_invitations",
            "ix_workspace_invitations_invitation_code_hash",
        ):
            op.create_index(
                "ix_workspace_invitations_invitation_code_hash",
                "workspace_invitations",
                ["invitation_code_hash"],
                unique=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "workspace_invitations"):
        if _has_index(
            inspector,
            "workspace_invitations",
            "ix_workspace_invitations_invitation_code_hash",
        ):
            op.drop_index(
                "ix_workspace_invitations_invitation_code_hash",
                table_name="workspace_invitations",
            )
        inspector = sa.inspect(bind)
        if not _has_index(inspector, "workspace_invitations", "ix_workspace_invitations_code_hash"):
            op.create_index(
                "ix_workspace_invitations_code_hash",
                "workspace_invitations",
                ["invitation_code_hash"],
                unique=True,
            )

