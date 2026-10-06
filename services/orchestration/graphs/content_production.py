from langgraph.graph import StateGraph, START, END
from services.orchestration.state.base import ContentProductionState
from services.orchestration.nodes.production import generate_variants_node
from services.orchestration.nodes.quality import quality_gate_node

builder = StateGraph(ContentProductionState)

builder.add_node("generate_variants", generate_variants_node)
builder.add_node("quality_gate", quality_gate_node)

builder.add_edge(START, "generate_variants")
builder.add_edge("generate_variants", "quality_gate")
builder.add_edge("quality_gate", END)

graph = builder.compile()
