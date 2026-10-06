from langgraph.graph import StateGraph, START, END
from services.orchestration.state.base import AnalyticsState
from services.orchestration.nodes.analytics import normalize_metrics_node

builder = StateGraph(AnalyticsState)
builder.add_node("normalize_metrics", normalize_metrics_node)

builder.add_edge(START, "normalize_metrics")
builder.add_edge("normalize_metrics", END)

graph = builder.compile()
