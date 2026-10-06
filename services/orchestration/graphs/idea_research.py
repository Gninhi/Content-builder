from langgraph.graph import StateGraph, START, END
from services.orchestration.state.base import IdeaResearchState
from services.orchestration.nodes.research import collect_sources_node, ideation_and_scoring_node


builder = StateGraph(IdeaResearchState)

builder.add_node("collect_sources", collect_sources_node)
builder.add_node("ideate_and_score", ideation_and_scoring_node)

builder.add_edge(START, "collect_sources")
builder.add_edge("collect_sources", "ideate_and_score")
builder.add_edge("ideate_and_score", END)

graph = builder.compile()
