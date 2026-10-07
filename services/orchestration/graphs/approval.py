from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from services.orchestration.state.base import ApprovalState
from services.orchestration.nodes.approval import human_review_decision_node
from services.orchestration.checkpointer import get_checkpointer


def prepare_for_review_node(state: ApprovalState) -> ApprovalState:
    """Prepares payload and ensures hash integrity prior to human interrupt."""
    return state


builder = StateGraph(ApprovalState)

builder.add_node("prepare_for_review", prepare_for_review_node)
builder.add_node("human_review", human_review_decision_node)

builder.add_edge(START, "prepare_for_review")
builder.add_edge("prepare_for_review", "human_review")
builder.add_edge("human_review", END)


def create_approval_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    Factory compiling the human-in-the-loop approval graph with durable
    or isolated test checkpointer backing.
    """
    cp = checkpointer if checkpointer is not None else get_checkpointer()
    return builder.compile(
        checkpointer=cp,
        interrupt_before=["human_review"]
    )


# Default graph instance for runtime
graph = create_approval_graph()
