"""add_veille_runs_and_scheduling

Revision ID: 6d1e2f3a4b5c
Revises: 5c9d1e2f3a4b
Create Date: 2026-10-14 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d1e2f3a4b5c'
down_revision: Union[str, None] = '5c9d1e2f3a4b'
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
    # Create veille_runs table for persistent collection tracking and observability
    if not _has_table(inspector, 'veille_runs'):
        op.create_table(
            'veille_runs',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('workspace_id', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=32), nullable=False, server_default='RUNNING'),
            sa.Column('trigger_type', sa.String(length=32), nullable=False, server_default='SCHEDULED'),
            sa.Column('axis', sa.String(length=64), nullable=True),
            sa.Column('sources_contacted', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('sources_failed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('signals_discovered', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('signals_saved', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('signals_qualified', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('signals_rejected', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_summary', sa.Text(), nullable=True),
            sa.Column('execution_metrics', sa.JSON(), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    inspector = sa.inspect(bind)
    if not _has_index(inspector, 'veille_runs', 'ix_veille_runs_workspace_id'):
        op.create_index('ix_veille_runs_workspace_id', 'veille_runs', ['workspace_id'])
    if not _has_index(inspector, 'veille_runs', 'ix_veille_runs_status'):
        op.create_index('ix_veille_runs_status', 'veille_runs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_veille_runs_status', table_name='veille_runs')
    op.drop_index('ix_veille_runs_workspace_id', table_name='veille_runs')
    op.drop_table('veille_runs')
