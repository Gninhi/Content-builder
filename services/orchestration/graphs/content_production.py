from langgraph.graph import StateGraph, START, END
from services.orchestration.state.base import ContentProductionState
from services.orchestration.nodes.production import generate_variants_node
from services.orchestration.nodes.quality import quality_gate_node


def _route_after_quality_gate(state: ContentProductionState) -> str:
    """
    Bounded reflexive routing (D-04 & Section 7.1):
    - If QA passed (`overall_passed` is True), terminate.
    - If QA failed (`overall_passed` is False) and `qa_attempt <= max_qa_retries` (default 1 retry = 2 total passes),
      route back to `generate_variants` with `qa_feedback_history` injected.
    - Otherwise terminate with `QA_FAILED`.
    """
    qa_results = state.get("qa_results") or {}
    if qa_results.get("overall_passed", False):
        return END

    qa_attempt = int(state.get("qa_attempt") or 1)
    raw_max_retries = state.get("max_qa_retries")
    max_retries = int(raw_max_retries) if raw_max_retries is not None else 1
    if qa_attempt <= max_retries:
        budget = state.get("cycle_budget")
        if budget is not None:
            used_tokens = int(getattr(budget, "used_tokens", 0))
            max_tokens = int(getattr(budget, "max_tokens", 50000))
            if used_tokens >= max_tokens:
                return END
        return "generate_variants"

    return END


builder = StateGraph(ContentProductionState)

builder.add_node("generate_variants", generate_variants_node)
builder.add_node("quality_gate", quality_gate_node)

builder.add_edge(START, "generate_variants")
builder.add_edge("generate_variants", "quality_gate")
builder.add_conditional_edges(
    "quality_gate",
    _route_after_quality_gate,
    {
        "generate_variants": "generate_variants",
        END: END,
    },
)

graph = builder.compile()

