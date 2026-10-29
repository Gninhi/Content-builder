from langgraph.graph import StateGraph, START, END
from services.orchestration.state.base import IdeaResearchState
from services.orchestration.nodes.research import (
    collect_sources_node,
    evidence_enrichment_node,
    ideation_and_scoring_node,
)


def _route_after_enrichment(state: IdeaResearchState) -> str:
    """
    Bounded conditional routing after evidence_enrichment (Section 8.2 & D-04):
    - Never exceeds 2 tool calls (`enrichment_count < 2`).
    - Continues enrichment if `enable_agentic_enrichment` is active and last step performed a tool call
      without reaching "proceed".
    """
    count = int(state.get("enrichment_count") or 0)
    if count >= 2:
        return "ideate_and_score"
    history = state.get("enrichment_history") or []
    if not history:
        return "ideate_and_score"
    last_action = history[-1].get("action")
    if state.get("enable_agentic_enrichment") and last_action in ("search_web", "browse_url"):
        return "evidence_enrichment"
    return "ideate_and_score"


builder = StateGraph(IdeaResearchState)

builder.add_node("collect_sources", collect_sources_node)
builder.add_node("evidence_enrichment", evidence_enrichment_node)
builder.add_node("ideate_and_score", ideation_and_scoring_node)

builder.add_edge(START, "collect_sources")
builder.add_edge("collect_sources", "evidence_enrichment")
builder.add_conditional_edges(
    "evidence_enrichment",
    _route_after_enrichment,
    {
        "evidence_enrichment": "evidence_enrichment",
        "ideate_and_score": "ideate_and_score",
    },
)
builder.add_edge("ideate_and_score", END)

graph = builder.compile()
