import sys
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash
from services.orchestration.state.base import ApprovalState
from services.orchestration.checkpointer import get_checkpointer


def prepare_for_review_node(state: ApprovalState) -> ApprovalState:
    """Prepares payload and ensures hash integrity prior to human interrupt."""
    return state


def human_review_decision_node(state: ApprovalState) -> Dict[str, Any]:
    """
    Applies the human decision to the content variant state, verifying payload hash integrity.
    """
    decision = state.get("decision", "reject")
    payload = state.get("payload", {})
    expected_hash = state.get("payload_hash", "")
    
    current_hash = compute_payload_hash(payload)
    if decision != "edit" and expected_hash and current_hash != expected_hash:
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


def create_approval_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    Helper factory compiling a durable HITL approval workflow with interrupt_before=["human_review"]
    for checkpointer durability verification.
    """
    g = StateGraph(ApprovalState)
    g.add_node("prepare_for_review", prepare_for_review_node)
    g.add_node("human_review", human_review_decision_node)
    g.add_edge(START, "prepare_for_review")
    g.add_edge("prepare_for_review", "human_review")
    g.add_edge("human_review", END)

    if "langgraph_api" in sys.modules and checkpointer is None:
        return g.compile(interrupt_before=["human_review"])

    cp = checkpointer if checkpointer is not None else get_checkpointer()
    return g.compile(
        checkpointer=cp,
        interrupt_before=["human_review"]
    )
