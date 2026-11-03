"""add_workspace_llm_settings

Revision ID: 3a7b9c1d2e4f
Revises: 286e614508c4
Create Date: 2026-10-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a7b9c1d2e4f'
down_revision: Union[str, None] = '286e614508c4'
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
    if not _has_table(inspector, 'workspace_llm_settings'):
        op.create_table(
            'workspace_llm_settings',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('workspace_id', sa.String(length=64), nullable=False),
            sa.Column('default_provider_id', sa.String(length=64), nullable=False),
            sa.Column('default_model_id', sa.String(length=128), nullable=False),
            sa.Column('default_temperature', sa.Float(), nullable=False),
            sa.Column('task_overrides', sa.JSON(), nullable=False),
            sa.Column('provider_settings', sa.JSON(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('workspace_id', name='uq_workspace_llm_settings_ws')
        )
    inspector = sa.inspect(bind)
    if not _has_index(inspector, 'workspace_llm_settings', 'ix_workspace_llm_settings_workspace_id'):
        op.create_index(op.f('ix_workspace_llm_settings_workspace_id'), 'workspace_llm_settings', ['workspace_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_workspace_llm_settings_workspace_id'), table_name='workspace_llm_settings')
    op.drop_table('workspace_llm_settings')
