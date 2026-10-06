from typing import Dict, Any
from packages.domain.state_machine import ContentStatus, ContentStateMachine
from packages.domain.idempotency import compute_payload_hash
from services.orchestration.state.base import ApprovalState


def human_review_decision_node(state: ApprovalState) -> Dict[str, Any]:
    """
    Applies the human decision to the content variant state, verifying payload hash integrity.
    """
    decision = state.get("decision", "reject")
    payload = state.get("payload", {})
    expected_hash = state.get("payload_hash", "")
    
    current_hash = compute_payload_hash(payload)
    if expected_hash and current_hash != expected_hash:
        return {
            "status": ContentStatus.QA_FAILED,
            "feedback": "Payload hash mismatch: content was modified without re-evaluation."
        }

    if decision == "approve":
        return {"status": ContentStatus.APPROVED}
    elif decision == "reject":
        return {"status": ContentStatus.REJECTED}
    elif decision in ("rewrite", "request_rewrite"):
        return {"status": ContentStatus.REWRITE_REQUESTED}
    elif decision == "edit":
        # Edited content is re-approved with new hash
        new_hash = compute_payload_hash(payload)
        return {
            "status": ContentStatus.APPROVED,
            "payload_hash": new_hash
        }
    else:
        return {"status": ContentStatus.IN_REVIEW}
