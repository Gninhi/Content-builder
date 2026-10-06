from langgraph.graph import StateGraph, START, END
from services.orchestration.state.base import ContentProductionState
from services.orchestration.nodes.quality import quality_gate_node

builder = StateGraph(ContentProductionState)
builder.add_node("quality_gate", quality_gate_node)
builder.add_edge(START, "quality_gate")
builder.add_edge("quality_gate", END)

graph = builder.compile()
