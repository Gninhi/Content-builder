"""add_auth_verification_and_refresh_tokens

Revision ID: 5c9d1e2f3a4b
Revises: 4b8c0d2e3f1a
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c9d1e2f3a4b'
down_revision: Union[str, None] = '4b8c0d2e3f1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add auth verification & consent fields to users
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('email_verification_token_hash', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('email_verification_expires_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('password_reset_token_hash', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('cgu_accepted_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('cgu_version', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('privacy_accepted_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('privacy_version', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))
        batch_op.create_index('ix_users_email_verification_token_hash', ['email_verification_token_hash'])
        batch_op.create_index('ix_users_password_reset_token_hash', ['password_reset_token_hash'])

    # 2. Add is_demo and expires_at to workspaces
    with op.batch_alter_table('workspaces') as batch_op:
        batch_op.add_column(sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))

    # 3. Create user_refresh_tokens table
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
    op.create_index('ix_user_refresh_tokens_user_id', 'user_refresh_tokens', ['user_id'])
    op.create_index('ix_user_refresh_tokens_token_hash', 'user_refresh_tokens', ['token_hash'], unique=True)
    op.create_index('ix_user_refresh_tokens_family_id', 'user_refresh_tokens', ['family_id'])

    # 4. Create workspace_invitations table
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
    op.create_index('ix_workspace_invitations_workspace_id', 'workspace_invitations', ['workspace_id'])
    op.create_index('ix_workspace_invitations_email', 'workspace_invitations', ['email'])
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
