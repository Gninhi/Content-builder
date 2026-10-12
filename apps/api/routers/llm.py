import logging
from typing import List, Optional, Dict, Any, cast
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from packages.contracts.llm import (
    LLMProviderInfo,
    LLMModelInfo,
    WorkspaceLLMConfigResponse,
    WorkspaceLLMConfigRequest,
    LLMConnectionTestRequest,
    LLMConnectionTestResponse,
    LLMValidationRequest,
    LLMValidationResponse,
    TaskLLMOverride,
)
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository
from services.orchestration.providers.registry import LLMProviderRegistry
from services.orchestration.providers.nvidia import validate_nvidia_endpoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/llm", tags=["LLM Providers & Models"])


@router.get("/providers", response_model=List[LLMProviderInfo])
def list_providers(
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
) -> List[LLMProviderInfo]:
    """
    Returns available LLM providers and their configuration status.
    Strictly sanitizes secrets: no credentials or API keys are ever returned.
    """
    return LLMProviderRegistry.get_all_provider_info()


@router.get("/models", response_model=List[LLMModelInfo])
def list_models(
    provider_id: Optional[str] = Query(None, description="Optional provider identifier filter (e.g. 'gemini', 'nvidia')"),
    refresh: bool = Query(False, description="Force refresh of live discovered models"),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
) -> List[LLMModelInfo]:
    """
    Returns available models from the curated catalogue or live discovery endpoints.
    """
    if provider_id:
        adapter = LLMProviderRegistry.get_adapter(provider_id)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"LLM Provider '{provider_id}' is not registered.")
        return adapter.list_models(force_refresh=refresh)

    return LLMProviderRegistry.list_models(force_refresh=refresh)


@router.get("/config/{workspace_id}", response_model=WorkspaceLLMConfigResponse)
def get_workspace_llm_config(
    workspace_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
) -> WorkspaceLLMConfigResponse:
    """
    Retrieves the persisted LLM configuration for a specific workspace.
    Falls back to system defaults if no custom configuration has been saved.
    """
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Forbidden workspace configuration access.")

    db_settings = repo.get_workspace_llm_settings(workspace_id)
    if db_settings:
        raw_overrides: Dict[str, Any] = cast(Dict[str, Any], db_settings.task_overrides or {})
        typed_overrides = {}
        for task, data in raw_overrides.items():
            if isinstance(data, dict):
                typed_overrides[task] = TaskLLMOverride(
                    provider_id=data.get("provider_id", "gemini"),
                    model_id=data.get("model_id", "gemini-3.8-flash"),
                    temperature=data.get("temperature"),
                    inherit_default=data.get("inherit_default", False),
                )
        return WorkspaceLLMConfigResponse(
            workspace_id=workspace_id,
            default_provider_id=str(db_settings.default_provider_id),
            default_model_id=str(db_settings.default_model_id),
            default_temperature=float(db_settings.default_temperature),
            task_overrides=typed_overrides,
            provider_settings=dict(db_settings.provider_settings or {}),
            updated_at=cast(Optional[datetime], db_settings.updated_at),
        )

    # Return system baseline if no custom settings exist
    return WorkspaceLLMConfigResponse(
        workspace_id=workspace_id,
        default_provider_id="gemini",
        default_model_id="gemini-3.8-flash",
        default_temperature=0.2,
        task_overrides={},
        provider_settings={},
        updated_at=None,
    )


@router.put("/config/{workspace_id}", response_model=WorkspaceLLMConfigResponse)
def update_workspace_llm_config(
    workspace_id: str,
    req: WorkspaceLLMConfigRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner"))
) -> WorkspaceLLMConfigResponse:
    """
    Updates and persists LLM configuration for the workspace.
    Validates providers, models, parameter ranges, and guards against SSRF.
    """
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Forbidden workspace configuration access.")

    # 1. Validate default provider
    adapter = LLMProviderRegistry.get_adapter(req.default_provider_id)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"Invalid provider_id: '{req.default_provider_id}'.")
    if not adapter.is_enabled():
        raise HTTPException(status_code=400, detail=f"Provider '{req.default_provider_id}' is currently disabled.")

    # 2. Validate default model
    if not adapter.validate_model(req.default_model_id):
        raise HTTPException(
            status_code=400,
            detail=f"Model '{req.default_model_id}' is not recognized or supported by provider '{req.default_provider_id}'."
        )

    # 3. Validate task overrides
    serialized_overrides: Dict[str, Any] = {}
    for task_name, override in req.task_overrides.items():
        if override.inherit_default:
            serialized_overrides[task_name] = override.model_dump()
            continue

        override_adapter = LLMProviderRegistry.get_adapter(override.provider_id)
        if not override_adapter:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid override provider '{override.provider_id}' for task '{task_name}'."
            )
        if not override_adapter.validate_model(override.model_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid override model '{override.model_id}' for task '{task_name}' on provider '{override.provider_id}'."
            )
        serialized_overrides[task_name] = override.model_dump()

    # 4. Validate custom provider settings (SSRF checks)
    for p_id, p_settings in req.provider_settings.items():
        if p_id == "nvidia" and "base_url" in p_settings:
            custom_url = p_settings["base_url"]
            try:
                validate_nvidia_endpoint(custom_url)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid custom endpoint for NVIDIA: {str(e)}"
                )

    # 5. Persist settings
    updated = repo.upsert_workspace_llm_settings(
        workspace_id=workspace_id,
        default_provider_id=req.default_provider_id,
        default_model_id=req.default_model_id,
        default_temperature=req.default_temperature,
        task_overrides=serialized_overrides,
        provider_settings=req.provider_settings,
    )

    # 6. Audit logging without secrets
    logger.info(
        f"AUDIT: LLM configuration updated by user '{user.user_id}' (role: {user.role}) "
        f"for workspace '{workspace_id}': default={req.default_provider_id}:{req.default_model_id}, "
        f"tasks_overridden={list(req.task_overrides.keys())}"
    )

    return WorkspaceLLMConfigResponse(
        workspace_id=workspace_id,
        default_provider_id=str(updated.default_provider_id),
        default_model_id=str(updated.default_model_id),
        default_temperature=float(updated.default_temperature),
        task_overrides=req.task_overrides,
        provider_settings=dict(updated.provider_settings or {}),
        updated_at=cast(Optional[datetime], updated.updated_at),
    )


@router.post("/test-connection", response_model=LLMConnectionTestResponse)
def test_connection(
    req: LLMConnectionTestRequest,
    user: UserContext = Depends(require_roles("Owner", "Editor"))
) -> LLMConnectionTestResponse:
    """
    Explicitly tests connectivity and authentication to an LLM provider.
    STRICT NOTICE: This is an explicit diagnostic endpoint that must ONLY be triggered
    by explicit user action. It must NEVER run automatically on page load or background poll.
    """
    adapter = LLMProviderRegistry.get_adapter(req.provider_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Provider '{req.provider_id}' is not recognized.")

    # Guard custom URL if provided
    if req.custom_base_url and req.provider_id == "nvidia":
        try:
            validate_nvidia_endpoint(req.custom_base_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid custom endpoint: {str(e)}")

    logger.info(f"Explicit LLM connection test triggered by user '{user.user_id}' for provider '{req.provider_id}'")
    return adapter.test_connection(
        model_id=req.model_id,
        custom_base_url=req.custom_base_url,
    )


@router.post("/validate-selection", response_model=LLMValidationResponse)
def validate_model_selection(
    req: LLMValidationRequest,
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
) -> LLMValidationResponse:
    """
    Validates whether a selected provider + model tuple supports the required capabilities
    (e.g., structured_output, text_generation).
    """
    adapter = LLMProviderRegistry.get_adapter(req.provider_id)
    if not adapter:
        return LLMValidationResponse(
            valid=False,
            provider_id=req.provider_id,
            model_id=req.model_id,
            missing_capabilities=req.required_capabilities,
            unknown_capabilities=[],
            message=f"Provider '{req.provider_id}' is not registered."
        )

    models = adapter.list_models()
    model_info = next((m for m in models if m.model_id == req.model_id), None)

    if not model_info:
        # Check if model is valid per adapter rule
        if not adapter.validate_model(req.model_id):
            return LLMValidationResponse(
                valid=False,
                provider_id=req.provider_id,
                model_id=req.model_id,
                missing_capabilities=req.required_capabilities,
                unknown_capabilities=[],
                message=f"Model '{req.model_id}' is not supported by provider '{req.provider_id}'."
            )
        # Custom model with unknown capabilities
        return LLMValidationResponse(
            valid=True,
            provider_id=req.provider_id,
            model_id=req.model_id,
            missing_capabilities=[],
            unknown_capabilities=req.required_capabilities,
            message="Modèle valide mais capacités non indexées (statut: UNKNOWN)."
        )

    missing = []
    unknown = []
    for cap in req.required_capabilities:
        val = model_info.capabilities.get(cap)
        if val is False:
            missing.append(cap)
        elif val is None:
            unknown.append(cap)

    if missing:
        return LLMValidationResponse(
            valid=False,
            provider_id=req.provider_id,
            model_id=req.model_id,
            missing_capabilities=missing,
            unknown_capabilities=unknown,
            message=f"Le modèle ne prend pas en charge : {', '.join(missing)}."
        )

    return LLMValidationResponse(
        valid=True,
        provider_id=req.provider_id,
        model_id=req.model_id,
        missing_capabilities=[],
        unknown_capabilities=unknown,
        message="Sélection valide pour les capacités requises."
    )
