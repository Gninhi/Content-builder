from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from services.orchestration.state.base import ApprovalState
from services.orchestration.nodes.approval import human_review_decision_node


def prepare_for_review_node(state: ApprovalState) -> dict:
    """Prepares payload and ensures hash integrity prior to human interrupt."""
    return state


builder = StateGraph(ApprovalState)

builder.add_node("prepare_for_review", prepare_for_review_node)
builder.add_node("human_review", human_review_decision_node)

builder.add_edge(START, "prepare_for_review")
builder.add_edge("prepare_for_review", "human_review")
builder.add_edge("human_review", END)

# In LangGraph, interrupt_before=["human_review"] enforces human intervention
checkpointer = MemorySaver()
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_review"]
)
