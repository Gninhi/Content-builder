import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import infra.db.models
from infra.db.models import (
    Base,
    ContentSourceModel,
    IdeaModel,
    ContentBriefModel,
    ContentPackageModel,
    ContentVariantModel,
    ApprovalModel,
    PublicationJobModel,
    PublishedPostModel,
    MetricSnapshotModel,
    VeilleSourceModel,
    SignalModel,
)


def test_models_have_explicit_foreign_key_and_composite_indexes():
    """Validates that SQLAlchemy models declare explicit indexes on foreign keys and composite status."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    def get_indexed_columns(table_name: str):
        indexes = inspector.get_indexes(table_name)
        # Returns set of single column names indexed, and tuples of composite columns
        single_cols = set()
        composite_cols = set()
        for idx in indexes:
            cols = tuple(idx["column_names"])
            if len(cols) == 1:
                single_cols.add(cols[0])
            elif len(cols) > 1:
                composite_cols.add(cols)
        return single_cols, composite_cols

    # 1. Foreign key index checks
    pub_single, pub_comp = get_indexed_columns("publication_jobs")
    assert "variant_id" in pub_single, "publication_jobs.variant_id must be indexed"
    assert ("status", "scheduled_at") in pub_comp, "publication_jobs must have composite index on (status, scheduled_at)"

    var_single, var_comp = get_indexed_columns("content_variants")
    assert "package_id" in var_single, "content_variants.package_id must be indexed"
    assert ("package_id", "status") in var_comp, "content_variants must have composite index on (package_id, status)"

    app_single, _ = get_indexed_columns("approvals")
    assert "variant_id" in app_single, "approvals.variant_id must be indexed"

    brief_single, _ = get_indexed_columns("content_briefs")
    assert "workspace_id" in brief_single, "content_briefs.workspace_id must be indexed"
    assert "idea_id" in brief_single, "content_briefs.idea_id must be indexed"

    pkg_single, _ = get_indexed_columns("content_packages")
    assert "brief_id" in pkg_single, "content_packages.brief_id must be indexed"

    src_single, _ = get_indexed_columns("content_sources")
    assert "workspace_id" in src_single, "content_sources.workspace_id must be indexed"

    idea_single, idea_comp = get_indexed_columns("ideas")
    assert "workspace_id" in idea_single, "ideas.workspace_id must be indexed"
    assert ("workspace_id", "status") in idea_comp, "ideas must have composite index on (workspace_id, status)"

    post_single, _ = get_indexed_columns("published_posts")
    assert "job_id" in post_single, "published_posts.job_id must be indexed"

    snap_single, _ = get_indexed_columns("metric_snapshots")
    assert "post_id" in snap_single, "metric_snapshots.post_id must be indexed"

    bp_single, _ = get_indexed_columns("brand_profiles")
    assert "workspace_id" in bp_single, "brand_profiles.workspace_id must be indexed"

    sig_single, sig_comp = get_indexed_columns("signals")
    assert "workspace_id" in sig_single, "signals.workspace_id must be indexed"
    assert ("workspace_id", "status") in sig_comp, "signals must have composite index on (workspace_id, status)"


def test_alembic_head_includes_foreign_key_and_composite_indexes():
    """Validates that Alembic migration upgrade to head creates all FK and composite indexes."""
    import tempfile
    import os
    from alembic.config import Config
    from alembic import command

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{path}"

    try:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", db_url)

        # Upgrade to head
        command.upgrade(config, "head")

        engine = create_engine(db_url)
        inspector = inspect(engine)

        pub_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("publication_jobs")}
        assert ("variant_id",) in pub_indexes
        assert ("status", "scheduled_at") in pub_indexes

        var_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("content_variants")}
        assert ("package_id",) in var_indexes
        assert ("package_id", "status") in var_indexes

        app_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("approvals")}
        assert ("variant_id",) in app_indexes

        brief_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("content_briefs")}
        assert ("workspace_id",) in brief_indexes
        assert ("idea_id",) in brief_indexes

        pkg_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("content_packages")}
        assert ("brief_id",) in pkg_indexes

        src_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("content_sources")}
        assert ("workspace_id",) in src_indexes

        idea_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("ideas")}
        assert ("workspace_id",) in idea_indexes
        assert ("workspace_id", "status") in idea_indexes

        bp_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("brand_profiles")}
        assert ("workspace_id",) in bp_indexes

        post_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("published_posts")}
        assert ("job_id",) in post_indexes

        snap_indexes = {tuple(idx["column_names"]) for idx in inspector.get_indexes("metric_snapshots")}
        assert ("post_id",) in snap_indexes

        # Clean downgrade to base then re-upgrade
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        if os.path.exists(path):
            os.remove(path)
