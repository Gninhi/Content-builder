from fastapi import APIRouter, Depends
from typing import List
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
    content = req.raw_text or f"Contenu automatique extrait depuis {req.url}"
    processed = WebExtractorConnector.process_source(
        source_type=req.type,
        content=content,
        url=req.url,
        author=req.author,
        workspace_id=req.workspace_id
    )

    source = repo.add_source(
        workspace_id=req.workspace_id,
        source_type=processed["type"],
        raw_content_ref=processed["raw_content_ref"],
        extracted_facts=processed["extracted_facts"],
        provenance=processed["provenance"],
        canonical_url=processed["canonical_url"]
    )

    return SourceResponse(
        id=source.id,
        workspace_id=source.workspace_id,
        type=source.type,
        canonical_url=source.canonical_url,
        raw_content_ref=source.raw_content_ref,
        extracted_facts=source.extracted_facts,
        provenance=source.provenance,
        status=source.status,
        created_at=source.created_at
    )


@router.get("/v1/sources", response_model=List[SourceResponse])
def list_sources(
    workspace_id: str = "ws_default",
    repo: ContentOpsRepository = Depends(get_repository)
):
    sources = repo.list_sources(workspace_id)
    return [
        SourceResponse(
            id=s.id,
            workspace_id=s.workspace_id,
            type=s.type,
            canonical_url=s.canonical_url,
            raw_content_ref=s.raw_content_ref,
            extracted_facts=s.extracted_facts,
            provenance=s.provenance,
            status=s.status,
            created_at=s.created_at
        ) for s in sources
    ]
