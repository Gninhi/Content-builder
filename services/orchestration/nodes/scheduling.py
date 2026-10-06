from typing import Dict, Any
import uuid
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_idempotency_key
from services.orchestration.state.base import SchedulingState


def schedule_job_node(state: SchedulingState) -> Dict[str, Any]:
    """
    Schedules an approved content variant for publication.
    Enforces idempotency and status prerequisites.
    """
    current_status = state.get("status")
    if current_status != ContentStatus.APPROVED:
        return {
            "error": f"Cannot schedule: variant status is {current_status}, must be APPROVED.",
            "status": current_status
        }

    workspace_id = state.get("workspace_id", "default")
    variant_id = state.get("variant_id", "")
    platform = state.get("platform", "linkedin")
    scheduled_at = state.get("scheduled_at", "")

    idempotency_key = compute_idempotency_key(
        workspace_id=workspace_id,
        variant_id=variant_id,
        platform=platform,
        scheduled_at=scheduled_at,
        version=1
    )

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    return {
        "job_id": job_id,
        "idempotency_key": idempotency_key,
        "status": ContentStatus.SCHEDULED,
        "error": None
    }
