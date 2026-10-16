from datetime import datetime, timezone, timedelta
import pytest
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import PublicationJobModel
from packages.domain.state_machine import ContentStatus
from apps.api.main import lifespan, app


@pytest.mark.asyncio
async def test_startup_only_reconciles_stale_publishing_jobs():
    """
    C9: Startup lifespan must NOT blindly transition freshly active PUBLISHING jobs to PUBLISH_UNKNOWN.
    Only stale jobs exceeding PUBLISHING_STALE_GRACE_MINUTES (default 15m) should transition.
    """
    now = datetime.now(timezone.utc)

    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Lifespan Test WS", "UTC", "owner_lifespan")
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Lifespan", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)

        # Fresh variant & job (1 minute ago)
        var_fresh = repo.add_variant(pkg.id, "linkedin", "Hook fresh", "Body fresh content", "CTA", ["#Fresh"], {})
        var_fresh.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(var_fresh.id, "approve", "owner_lifespan", ws.id)
        job_fresh = repo.schedule_publication(ws.id, var_fresh.id, now - timedelta(minutes=1))
        job_fresh.status = ContentStatus.PUBLISHING.value
        var_fresh.status = ContentStatus.PUBLISHING.value

        # Stale variant & job (30 minutes ago)
        var_stale = repo.add_variant(pkg.id, "linkedin", "Hook stale", "Body stale content", "CTA", ["#Stale"], {})
        var_stale.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(var_stale.id, "approve", "owner_lifespan", ws.id)
        job_stale = repo.schedule_publication(ws.id, var_stale.id, now - timedelta(minutes=30))
        job_stale.status = ContentStatus.PUBLISHING.value
        var_stale.status = ContentStatus.PUBLISHING.value

        db.commit()

        fresh_id = job_fresh.id
        stale_id = job_stale.id

    # Execute startup lifespan
    async with lifespan(app):
        pass

    with get_db_session() as db:
        j_fresh = db.query(PublicationJobModel).filter_by(id=fresh_id).first()
        j_stale = db.query(PublicationJobModel).filter_by(id=stale_id).first()

        # The fresh job must NOT be converted to PUBLISH_UNKNOWN
        assert j_fresh.status == ContentStatus.PUBLISHING.value

        # The stale job (> 15 min) MUST be safely transitioned to PUBLISH_UNKNOWN
        assert j_stale.status == ContentStatus.PUBLISH_UNKNOWN.value
