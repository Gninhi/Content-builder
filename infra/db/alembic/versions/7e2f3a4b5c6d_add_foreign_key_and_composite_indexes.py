"""add_foreign_key_and_composite_indexes

Revision ID: 7e2f3a4b5c6d
Revises: 6d1e2f3a4b5c
Create Date: 2026-10-16 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e2f3a4b5c6d'
down_revision: Union[str, None] = '6d1e2f3a4b5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Foreign key and composite status indexes to prevent table scans and cascade locks
    op.create_index('ix_brand_profiles_workspace_id', 'brand_profiles', ['workspace_id'])
    op.create_index('ix_content_sources_workspace_id', 'content_sources', ['workspace_id'])
    op.create_index('ix_ideas_workspace_id', 'ideas', ['workspace_id'])
    op.create_index('ix_ideas_workspace_status', 'ideas', ['workspace_id', 'status'])
    op.create_index('ix_content_briefs_workspace_id', 'content_briefs', ['workspace_id'])
    op.create_index('ix_content_briefs_idea_id', 'content_briefs', ['idea_id'])
    op.create_index('ix_content_packages_brief_id', 'content_packages', ['brief_id'])
    op.create_index('ix_content_variants_package_id', 'content_variants', ['package_id'])
    op.create_index('ix_content_variants_package_status', 'content_variants', ['package_id', 'status'])
    op.create_index('ix_approvals_variant_id', 'approvals', ['variant_id'])
    op.create_index('ix_publication_jobs_variant_id', 'publication_jobs', ['variant_id'])
    op.create_index('ix_publication_jobs_status_scheduled_at', 'publication_jobs', ['status', 'scheduled_at'])
    op.create_index('ix_published_posts_job_id', 'published_posts', ['job_id'])
    op.create_index('ix_metric_snapshots_post_id', 'metric_snapshots', ['post_id'])


def downgrade() -> None:
    op.drop_index('ix_metric_snapshots_post_id', table_name='metric_snapshots')
    op.drop_index('ix_published_posts_job_id', table_name='published_posts')
    op.drop_index('ix_publication_jobs_status_scheduled_at', table_name='publication_jobs')
    op.drop_index('ix_publication_jobs_variant_id', table_name='publication_jobs')
    op.drop_index('ix_approvals_variant_id', table_name='approvals')
    op.drop_index('ix_content_variants_package_status', table_name='content_variants')
    op.drop_index('ix_content_variants_package_id', table_name='content_variants')
    op.drop_index('ix_content_packages_brief_id', table_name='content_packages')
    op.drop_index('ix_content_briefs_idea_id', table_name='content_briefs')
    op.drop_index('ix_content_briefs_workspace_id', table_name='content_briefs')
    op.drop_index('ix_ideas_workspace_status', table_name='ideas')
    op.drop_index('ix_ideas_workspace_id', table_name='ideas')
    op.drop_index('ix_content_sources_workspace_id', table_name='content_sources')
    op.drop_index('ix_brand_profiles_workspace_id', table_name='brand_profiles')
