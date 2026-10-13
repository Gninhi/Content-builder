from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LLMCapability(str, Enum):
    TEXT_GENERATION = "text_generation"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALLING = "tool_calling"
    STREAMING = "streaming"
    VISION = "vision"
    EMBEDDINGS = "embeddings"


class LLMParameterSpec(BaseModel):
    name: str
    param_type: str = "float"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_value: Optional[Any] = None
    description: Optional[str] = None


class LLMModelInfo(BaseModel):
    provider_id: str
    model_id: str
    full_id: str = ""
    display_name: str
    capabilities: Dict[str, Optional[bool]] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    provenance: str = "catalog"  # catalog, live_discovery, custom
    last_refreshed_at: datetime = Field(default_factory=utc_now)
    is_available: bool = True

    def model_post_init(self, __context: Any) -> None:
        if not self.full_id:
            self.full_id = f"{self.provider_id}:{self.model_id}"


class LLMProviderInfo(BaseModel):
    provider_id: str
    display_name: str
    adapter_type: str
    is_configured: bool
    is_enabled: bool
    base_url: Optional[str] = None
    default_model: str
    last_test_status: Optional[str] = None  # SUCCESS, ERROR, NOT_TESTED
    last_test_at: Optional[datetime] = None
    last_test_message: Optional[str] = None


class TaskLLMOverride(BaseModel):
    provider_id: str
    model_id: str
    temperature: Optional[float] = None
    inherit_default: bool = False


class WorkspaceLLMConfigResponse(BaseModel):
    workspace_id: str
    default_provider_id: str = "nvidia"
    default_model_id: str = "z-ai/glm-5.3-flash"
    default_temperature: float = 0.2
    task_overrides: Dict[str, TaskLLMOverride] = Field(default_factory=dict)
    provider_settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    updated_at: Optional[datetime] = None


class WorkspaceLLMConfigRequest(BaseModel):
    default_provider_id: str
    default_model_id: str
    default_temperature: float = Field(0.2, ge=0.0, le=2.0)
    task_overrides: Dict[str, TaskLLMOverride] = Field(default_factory=dict)
    provider_settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class LLMConnectionTestRequest(BaseModel):
    provider_id: str
    model_id: Optional[str] = None
    custom_base_url: Optional[str] = None


class LLMConnectionTestResponse(BaseModel):
    success: bool
    provider_id: str
    model_id: str
    latency_ms: float
    message: str
    tested_at: datetime = Field(default_factory=utc_now)


class LLMValidationRequest(BaseModel):
    provider_id: str
    model_id: str
    required_capabilities: List[str] = Field(default_factory=list)


class LLMValidationResponse(BaseModel):
    valid: bool
    provider_id: str
    model_id: str
    missing_capabilities: List[str] = Field(default_factory=list)
    unknown_capabilities: List[str] = Field(default_factory=list)
    message: str
