from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


class DomainEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    workspace_id: str
    aggregate_id: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    actor_type: str = Field(..., description="human, agent, or worker")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = "1.0"
    payload: Dict[str, Any] = Field(default_factory=dict)


# Standard Domain Event Factories
def create_domain_event(
    event_type: str,
    workspace_id: str,
    aggregate_id: str,
    actor_type: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> DomainEvent:
    return DomainEvent(
        event_type=event_type,
        workspace_id=workspace_id,
        aggregate_id=aggregate_id,
        actor_type=actor_type,
        correlation_id=correlation_id or str(uuid.uuid4()),
        payload=payload
    )
