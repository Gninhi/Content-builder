from langgraph.graph import StateGraph, START, END
from services.orchestration.state.base import SchedulingState
from services.orchestration.nodes.scheduling import schedule_job_node

builder = StateGraph(SchedulingState)
builder.add_node("schedule_job", schedule_job_node)

builder.add_edge(START, "schedule_job")
builder.add_edge("schedule_job", END)

graph = builder.compile()
