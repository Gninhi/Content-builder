"""add_auth_verification_and_refresh_tokens

Revision ID: 5c9d1e2f3a4b
Revises: 4b8c0d2e3f1a
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union, Any
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c9d1e2f3a4b'
down_revision: Union[str, None] = '4b8c0d2e3f1a'
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

    # 1. Add auth verification & consent fields to users
    user_cols_to_add: list[tuple[str, sa.Column[Any]]] = [
        ('email_verified', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false())),
        ('email_verification_token_hash', sa.Column('email_verification_token_hash', sa.String(length=128), nullable=True)),
        ('email_verification_expires_at', sa.Column('email_verification_expires_at', sa.DateTime(), nullable=True)),
        ('password_reset_token_hash', sa.Column('password_reset_token_hash', sa.String(length=128), nullable=True)),
        ('password_reset_expires_at', sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True)),
        ('cgu_accepted_at', sa.Column('cgu_accepted_at', sa.DateTime(), nullable=True)),
        ('cgu_version', sa.Column('cgu_version', sa.String(length=32), nullable=True)),
        ('privacy_accepted_at', sa.Column('privacy_accepted_at', sa.DateTime(), nullable=True)),
        ('privacy_version', sa.Column('privacy_version', sa.String(length=32), nullable=True)),
        ('failed_login_attempts', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0')),
        ('locked_until', sa.Column('locked_until', sa.DateTime(), nullable=True)),
    ]
    missing_user_cols = [col for name, col in user_cols_to_add if not _has_column(inspector, 'users', name)]
    if missing_user_cols:
        with op.batch_alter_table('users') as batch_op:
            for col in missing_user_cols:
                batch_op.add_column(col)

    inspector = sa.inspect(bind)
    if not _has_index(inspector, 'users', 'ix_users_email_verification_token_hash'):
        op.create_index('ix_users_email_verification_token_hash', 'users', ['email_verification_token_hash'])
    if not _has_index(inspector, 'users', 'ix_users_password_reset_token_hash'):
        op.create_index('ix_users_password_reset_token_hash', 'users', ['password_reset_token_hash'])

    # 2. Add is_demo and expires_at to workspaces
    ws_cols_to_add: list[tuple[str, sa.Column[Any]]] = [
        ('is_demo', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false())),
        ('expires_at', sa.Column('expires_at', sa.DateTime(), nullable=True)),
    ]
    missing_ws_cols = [col for name, col in ws_cols_to_add if not _has_column(inspector, 'workspaces', name)]
    if missing_ws_cols:
        with op.batch_alter_table('workspaces') as batch_op:
            for col in missing_ws_cols:
                batch_op.add_column(col)

    # 3. Create user_refresh_tokens table
    inspector = sa.inspect(bind)
    if not _has_table(inspector, 'user_refresh_tokens'):
        op.create_table(
            'user_refresh_tokens',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('user_id', sa.String(length=64), nullable=False),
            sa.Column('token_hash', sa.String(length=128), nullable=False),
            sa.Column('family_id', sa.String(length=64), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    inspector = sa.inspect(bind)
    if not _has_index(inspector, 'user_refresh_tokens', 'ix_user_refresh_tokens_user_id'):
        op.create_index('ix_user_refresh_tokens_user_id', 'user_refresh_tokens', ['user_id'])
    if not _has_index(inspector, 'user_refresh_tokens', 'ix_user_refresh_tokens_token_hash'):
        op.create_index('ix_user_refresh_tokens_token_hash', 'user_refresh_tokens', ['token_hash'], unique=True)
    if not _has_index(inspector, 'user_refresh_tokens', 'ix_user_refresh_tokens_family_id'):
        op.create_index('ix_user_refresh_tokens_family_id', 'user_refresh_tokens', ['family_id'])

    # 4. Create workspace_invitations table
    if not _has_table(inspector, 'workspace_invitations'):
        op.create_table(
            'workspace_invitations',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('workspace_id', sa.String(length=64), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=32), nullable=False, server_default='Editor'),
            sa.Column('invitation_code_hash', sa.String(length=128), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('accepted_at', sa.DateTime(), nullable=True),
            sa.Column('created_by', sa.String(length=64), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    inspector = sa.inspect(bind)
    if not _has_index(inspector, 'workspace_invitations', 'ix_workspace_invitations_workspace_id'):
        op.create_index('ix_workspace_invitations_workspace_id', 'workspace_invitations', ['workspace_id'])
    if not _has_index(inspector, 'workspace_invitations', 'ix_workspace_invitations_email'):
        op.create_index('ix_workspace_invitations_email', 'workspace_invitations', ['email'])
    if not _has_index(inspector, 'workspace_invitations', 'ix_workspace_invitations_code_hash') and not _has_index(
        inspector, 'workspace_invitations', 'ix_workspace_invitations_invitation_code_hash'
    ):
        op.create_index('ix_workspace_invitations_code_hash', 'workspace_invitations', ['invitation_code_hash'], unique=True)


def downgrade() -> None:
    op.drop_table('workspace_invitations')
    op.drop_table('user_refresh_tokens')
    with op.batch_alter_table('workspaces') as batch_op:
        batch_op.drop_column('expires_at')
        batch_op.drop_column('is_demo')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_password_reset_token_hash')
        batch_op.drop_index('ix_users_email_verification_token_hash')
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')
        batch_op.drop_column('privacy_version')
        batch_op.drop_column('privacy_accepted_at')
        batch_op.drop_column('cgu_version')
        batch_op.drop_column('cgu_accepted_at')
        batch_op.drop_column('password_reset_expires_at')
        batch_op.drop_column('password_reset_token_hash')
        batch_op.drop_column('email_verification_expires_at')
        batch_op.drop_column('email_verification_token_hash')
        batch_op.drop_column('email_verified')
