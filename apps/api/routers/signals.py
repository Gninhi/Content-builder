"""
Signals & Veille Technologique Router.
Provides endpoints for monitoring signal ingestion, qualification, filtering, and source registry CRUD.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository
from services.orchestration.veille.pipeline import VeillePipeline

router = APIRouter(prefix="/v1/signals", tags=["Veille Technologique & Signals"])


# --- Schemas ---
class SignalCollectRequest(BaseModel):
    axis: Optional[str] = Field(None, description="Target axis: 'ia', 'frameworks', or 'metiers'")
    demo: bool = Field(False, description="Whether to collect verified synthetic signals (no external calls)")
    custom_query: Optional[str] = Field(None, description="Optional custom search query")
    limit_per_axis: int = Field(3, ge=1, le=10, description="Max queries/items per axis")


class SignalStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: 'NEW', 'QUALIFIED', 'REJECTED', 'CONVERTED'")


class VeilleSourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    url: str = Field(..., min_length=5)
    axis: str = Field(..., description="'ia', 'frameworks', or 'metiers'")
    trust_level: str = Field("B", description="'A', 'B', or 'C'")
    source_type: str = Field("web", description="'web', 'rss', 'arxiv', 'github', 'hackernews', 'serpapi'")


class VeilleSourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    axis: Optional[str] = None
    trust_level: Optional[str] = None
    source_type: Optional[str] = None
    is_active: Optional[bool] = None
    health_status: Optional[str] = None


class SignalResponse(BaseModel):
    id: str
    workspace_id: str
    canonical_url: Optional[str]
    title: str
    summary: str
    axis: str
    trust_level: str
    qualification_score: float
    qualification_criteria: Dict[str, Any]
    facts: List[Dict[str, Any]]
    executive_takeaway: str
    status: str
    is_synthetic: bool
    created_at: str


class VeilleSourceResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    url: str
    axis: str
    trust_level: str
    source_type: str
    is_active: bool
    health_status: str
    created_at: str


def _serialize_signal(sig) -> Dict[str, Any]:
    return {
        "id": sig.id,
        "workspace_id": sig.workspace_id,
        "canonical_url": sig.canonical_url,
        "title": sig.title,
        "summary": sig.summary,
        "axis": sig.axis,
        "trust_level": sig.trust_level,
        "qualification_score": sig.qualification_score,
        "qualification_criteria": sig.qualification_criteria or {},
        "facts": sig.facts or [],
        "executive_takeaway": sig.executive_takeaway,
        "status": sig.status,
        "is_synthetic": sig.is_synthetic,
        "created_at": sig.created_at.isoformat() if sig.created_at else "",
    }


def _serialize_source(src) -> Dict[str, Any]:
    return {
        "id": src.id,
        "workspace_id": src.workspace_id,
        "name": src.name,
        "url": src.url,
        "axis": src.axis,
        "trust_level": src.trust_level,
        "source_type": src.source_type,
        "is_active": src.is_active,
        "health_status": src.health_status,
        "created_at": src.created_at.isoformat() if src.created_at else "",
    }


# --- Endpoints ---

@router.post("/collect", response_model=List[SignalResponse])
def trigger_collection(
    req: SignalCollectRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "ServiceAgent")),
):
    """Triggers an active monitoring collection and qualification cycle."""
    pipeline = VeillePipeline(repo)
    signals = pipeline.run_collection_cycle(
        workspace_id=user.workspace_id,
        axis=req.axis,
        demo=req.demo,
        custom_query=req.custom_query,
        limit_per_axis=req.limit_per_axis,
    )
    return [_serialize_signal(s) for s in signals]


@router.get("", response_model=List[SignalResponse])
def list_signals(
    axis: Optional[str] = Query(None, description="Filter by axis: 'ia', 'frameworks', 'metiers'"),
    trust_level: Optional[str] = Query(None, description="Filter by trust level: 'A', 'B', 'C'"),
    min_score: Optional[float] = Query(None, description="Minimum qualification score (0.0 to 5.0)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent")),
):
    """Lists monitoring signals with multi-criteria filtering."""
    signals = repo.list_signals(
        workspace_id=user.workspace_id,
        axis=axis,
        trust_level=trust_level,
        min_score=min_score,
        status=status_filter,
        limit=limit,
    )
    return [_serialize_signal(s) for s in signals]


@router.get("/sources", response_model=List[VeilleSourceResponse])
def list_sources(
    axis: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent")),
):
    """Lists configured monitoring sources for the workspace."""
    sources = repo.list_veille_sources(
        workspace_id=user.workspace_id,
        axis=axis,
        is_active=is_active,
    )
    return [_serialize_source(s) for s in sources]


@router.post("/sources", response_model=VeilleSourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    req: VeilleSourceCreateRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner")),
):
    """Creates a new monitoring source (strictly restricted to workspace Owner)."""
    src = repo.create_veille_source(
        workspace_id=user.workspace_id,
        name=req.name,
        url=req.url,
        axis=req.axis,
        trust_level=req.trust_level,
        source_type=req.source_type,
    )
    return _serialize_source(src)


@router.post("/sources/seed", response_model=List[VeilleSourceResponse])
def seed_default_sources(
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner")),
):
    """Seeds curated standard sources across IA, Frameworks, and Métiers (Owner only)."""
    sources = repo.seed_default_veille_sources(user.workspace_id)
    return [_serialize_source(s) for s in sources]


@router.put("/sources/{source_id}", response_model=VeilleSourceResponse)
def update_source(
    source_id: str,
    req: VeilleSourceUpdateRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner")),
):
    """Updates a monitoring source (strictly restricted to workspace Owner)."""
    updated = repo.update_veille_source(
        source_id=source_id,
        workspace_id=user.workspace_id,
        name=req.name,
        url=req.url,
        axis=req.axis,
        trust_level=req.trust_level,
        source_type=req.source_type,
        is_active=req.is_active,
        health_status=req.health_status,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Source not found.")
    return _serialize_source(updated)


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner")),
):
    """Deletes a monitoring source (strictly restricted to workspace Owner)."""
    success = repo.delete_veille_source(source_id=source_id, workspace_id=user.workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found.")
    return {"status": "deleted", "id": source_id}


@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(
    signal_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent")),
):
    """Retrieves full detail of a specific signal card."""
    sig = repo.get_signal(signal_id=signal_id, workspace_id=user.workspace_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return _serialize_signal(sig)


@router.patch("/{signal_id}/status", response_model=SignalResponse)
def update_signal_status(
    signal_id: str,
    req: SignalStatusUpdateRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor")),
):
    """Updates signal qualification status (QUALIFIED, REJECTED, CONVERTED)."""
    sig = repo.update_signal_status(
        signal_id=signal_id,
        workspace_id=user.workspace_id,
        status=req.status,
    )
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return _serialize_signal(sig)


@router.post("/{signal_id}/convert", status_code=status.HTTP_201_CREATED)
def convert_signal_to_idea_endpoint(
    signal_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor")),
):
    """
    Transactionally converts an approved monitoring signal into a verified editorial idea.
    Preserves factual provenance, signal-to-idea link, and guarantees idempotency against duplicate clicks.
    """
    try:
        idea = repo.convert_signal_to_idea(
            signal_id=signal_id,
            workspace_id=user.workspace_id,
        )
        return {
            "success": True,
            "message": "Signal converti en angle éditorial ancré avec succès.",
            "idea": {
                "id": idea.id,
                "title": idea.title,
                "angle": idea.angle,
                "pillar": idea.pillar,
                "audience": idea.audience,
                "evidence_refs": idea.evidence_refs,
                "novelty_score": idea.novelty_score,
                "relevance_score": idea.relevance_score,
                "effort_score": idea.effort_score,
                "total_score": idea.total_score,
                "priority": idea.priority,
                "signal_id": idea.signal_id,
                "status": idea.status,
            },
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la conversion du signal : {str(exc)}")

