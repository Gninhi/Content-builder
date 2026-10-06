from langgraph.graph import StateGraph, START, END
from typing import Dict, Any
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash
from packages.connectors.social.linkedin import LinkedInConnector
from packages.connectors.social.x_twitter import XTwitterConnector
from services.orchestration.state.base import PublishingState


def verify_approval_and_publish_node(state: PublishingState) -> Dict[str, Any]:
    """
    Controlled side-effect execution: validates approval hash match and delegates to social connector.
    """
    payload = state.get("payload", {})
    approval_hash = state.get("approval_hash", "")
    idempotency_key = state.get("idempotency_key", "")
    platform = state.get("platform", "linkedin")

    current_hash = compute_payload_hash(payload)
    if approval_hash and current_hash != approval_hash:
        return {
            "status": ContentStatus.PUBLISH_FAILED,
            "error": "Security failure: content payload has changed since human approval was granted."
        }

    try:
        if platform == "linkedin":
            connector = LinkedInConnector(sandbox_mode=True)
        elif platform == "x":
            connector = XTwitterConnector(sandbox_mode=True)
        else:
            raise ValueError(f"Unsupported publishing platform: {platform}")

        receipt = connector.publish(payload=payload, idempotency_key=idempotency_key)
        return {
            "status": ContentStatus.PUBLISHED,
            "receipt": receipt,
            "error": None
        }
    except Exception as e:
        return {
            "status": ContentStatus.PUBLISH_FAILED,
            "error": str(e)
        }


builder = StateGraph(PublishingState)
builder.add_node("verify_and_publish", verify_approval_and_publish_node)

builder.add_edge(START, "verify_and_publish")
builder.add_edge("verify_and_publish", END)

graph = builder.compile()
