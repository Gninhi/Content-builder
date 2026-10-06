from langgraph.graph import StateGraph, START, END
from services.orchestration.state.base import StrategyInsightsState
from services.orchestration.nodes.insights import generate_strategy_insights_node

builder = StateGraph(StrategyInsightsState)
builder.add_node("generate_insights", generate_strategy_insights_node)

builder.add_edge(START, "generate_insights")
builder.add_edge("generate_insights", END)

graph = builder.compile()
