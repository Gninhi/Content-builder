from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any, cast
from datetime import datetime
from packages.contracts.schemas import SourceIngestRequest, SourceResponse
from packages.connectors.sources.web_extractor import WebExtractorConnector
from packages.tools.browse import validate_target_url_security, fetch_safe_url, extract_metadata_and_text
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
    repo.ensure_workspace(ws_id)

    if req.url:
        try:
            validate_target_url_security(req.url)
        except (PermissionError, ValueError) as sec_err:
            raise HTTPException(status_code=400, detail=str(sec_err))

    content = (req.raw_text or "").strip()
    extraction_meta: Dict[str, Any] = {}
    extraction_status = "ingested"

    if not content:
        if req.type == "url" and req.url:
            try:
                resp = fetch_safe_url(req.url, timeout=10.0)
            except (PermissionError, ValueError) as sec_err:
                raise HTTPException(status_code=400, detail=str(sec_err))
            except Exception as net_err:
                raise HTTPException(
                    status_code=422,
                    detail=f"URL inaccessible ou en timeout : {net_err}",
                )

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=422,
                    detail=f"Échec de lecture de l'URL cible (HTTP {resp.status_code}).",
                )

            extraction_meta = extract_metadata_and_text(resp.text, str(resp.url))
            content = (extraction_meta.get("content") or "").strip()
            if len(content) < 40:
                raise HTTPException(
                    status_code=422,
                    detail="Contenu extrait vide ou insuffisant (< 40 caractères exploitables).",
                )
            extraction_status = "extracted"
        else:
            raise HTTPException(
                status_code=422,
                detail="Le champ raw_text est requis lorsqu'aucune URL extractible n'est fournie.",
            )

    processed = WebExtractorConnector.process_source(
        source_type=req.type,
        content=content,
        url=req.url,
        author=req.author,
        workspace_id=ws_id,
        extraction_status=extraction_status,
        metadata=extraction_meta,
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
    limit: int = Query(50, ge=1, le=100, description="Max sources to return (1-100)"),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    if workspace_id and workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Access to other workspace sources is forbidden.")
    sources = repo.list_sources(user.workspace_id, limit=limit)
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
