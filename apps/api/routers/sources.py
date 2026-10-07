from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, cast
from datetime import datetime
from packages.contracts.schemas import SourceIngestRequest, SourceResponse
from packages.connectors.sources.web_extractor import WebExtractorConnector
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository

router = APIRouter(tags=["Sources & Provenance"])


@router.post("/v1/sources", response_model=SourceResponse)
def ingest_source(
    req: SourceIngestRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    if req.workspace_id and req.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot ingest source for another workspace.")
    ws_id = user.workspace_id
    content = req.raw_text or f"Contenu automatique extrait depuis {req.url}"
    processed = WebExtractorConnector.process_source(
        source_type=req.type,
        content=content,
        url=req.url,
        author=req.author,
        workspace_id=ws_id
    )

    source = repo.add_source(
        workspace_id=ws_id,
        source_type=processed["type"],
        raw_content_ref=processed["raw_content_ref"],
        extracted_facts=processed["extracted_facts"],
        provenance=processed["provenance"],
        canonical_url=processed["canonical_url"]
    )

    return SourceResponse(
        id=str(source.id),
        workspace_id=str(source.workspace_id),
        type=str(source.type),
        canonical_url=str(source.canonical_url) if source.canonical_url else None,
        raw_content_ref=str(source.raw_content_ref),
        extracted_facts=list(source.extracted_facts),
        provenance=dict(source.provenance),
        status=str(source.status),
        created_at=cast(datetime, source.created_at)
    )


@router.get("/v1/sources", response_model=List[SourceResponse])
def list_sources(
    workspace_id: Optional[str] = None,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    if workspace_id and workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Access to other workspace sources is forbidden.")
    sources = repo.list_sources(user.workspace_id)
    return [
        SourceResponse(
            id=str(s.id),
            workspace_id=str(s.workspace_id),
            type=str(s.type),
            canonical_url=str(s.canonical_url) if s.canonical_url else None,
            raw_content_ref=str(s.raw_content_ref),
            extracted_facts=list(s.extracted_facts),
            provenance=dict(s.provenance),
            status=str(s.status),
            created_at=cast(datetime, s.created_at)
        ) for s in sources
    ]
