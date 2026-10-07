from fastapi import APIRouter, Depends, HTTPException, Body
from packages.contracts.schemas import (
    ApprovalRequest,
    ApprovalResponse,
)
from packages.domain.state_machine import ContentStatus
from services.orchestration.graphs.content_production import graph as content_production_graph
from packages.observability.tracing import ObservabilityTracer
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository
from infra.db.models import ContentVariantModel, ContentBriefModel

router = APIRouter(tags=["Content Production & Approvals"])


@router.post("/v1/content/generate")
def generate_content_package(
    brief_id: str = Body(..., embed=True),
    workspace_id: str = Body("ws_default", embed=True),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "ServiceAgent"))
):
    brief = repo.db.query(ContentBriefModel).filter(ContentBriefModel.id == brief_id).first()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found.")
    if brief.workspace_id != user.workspace_id and user.role.lower() != "owner":
        raise HTTPException(status_code=403, detail="Access to brief belonging to another workspace is forbidden.")

    workspace_id = brief.workspace_id
    brand_profile = repo.get_latest_brand_profile(workspace_id)
    voice = brand_profile.voice if brand_profile else "Expert et direct"
    prohibited = brand_profile.prohibited_topics if brand_profile else []
    cta_policy = brand_profile.cta_policy if brand_profile else {}

    sources = repo.list_sources(workspace_id)
    raw_sources = [
        {"canonical_url": s.canonical_url, "facts": s.extracted_facts}
        for s in sources
    ]

    initial_state = {
        "workspace_id": workspace_id,
        "brief_id": brief.id,
        "objective": brief.objective,
        "angle": "Perspective d'expert et retour terrain",
        "target_platforms": brief.platform_targets,
        "brand_voice": voice,
        "prohibited_topics": prohibited,
        "cta_policy": cta_policy,
        "sources": raw_sources,
        "requirements": brief.requirements,
        "generated_variants": [],
        "qa_results": {},
        "status": ContentStatus.DRAFT,
        "run_id": "run_prod_1",
        "errors": []
    }

    # Run LangGraph content production and quality gate workflow with Langfuse tracing
    callback = ObservabilityTracer.get_callback_handler()
    config = {"callbacks": [callback]} if callback else {}
    exec_result = content_production_graph.invoke(initial_state, config=config)

    qa_info = exec_result.get("qa_results", {})
    package_status = exec_result.get("status", ContentStatus.DRAFT)

    package = repo.create_content_package(
        brief_id=brief.id,
        version=1,
        model_metadata={"orchestrator": "LangGraph", "voice": voice},
        qa_score=qa_info.get("overall_score", 90.0)
    )
    package.status = package_status.value
    repo.db.commit()

    # Record QA gate evaluation score in Langfuse
    ObservabilityTracer.record_score(
        name="qa_gate_score",
        value=qa_info.get("overall_score", 90.0) / 100.0,
        trace_id=package.id,
        comment=f"Deterministic and semantic QA evaluation for package {package.id}"
    )

    saved_variants = []
    for var in exec_result.get("generated_variants", []):
        variant_model = repo.add_variant(
            package_id=package.id,
            platform=var["platform"],
            hook=var["hook"],
            body=var["body"],
            cta=var["cta"],
            hashtags=var.get("hashtags", []),
            media_spec=var.get("media_spec", {}),
            claims=var.get("claims", [])
        )
        # Update variant status based on QA
        variant_model.status = var.get("status", ContentStatus.IN_REVIEW.value)
        repo.db.commit()
        repo.db.refresh(variant_model)

        saved_variants.append({
            "id": variant_model.id,
            "platform": variant_model.platform,
            "hook": variant_model.hook,
            "body": variant_model.body,
            "cta": variant_model.cta,
            "hashtags": variant_model.hashtags,
            "media_spec": variant_model.media_spec,
            "claims": variant_model.claims,
            "payload_hash": variant_model.payload_hash,
            "status": variant_model.status,
            "qa_score": var.get("qa_score", 100.0),
            "checks": var.get("checks", [])
        })

    return {
        "id": package.id,
        "brief_id": package.brief_id,
        "version": package.version,
        "status": package.status,
        "qa_score": package.qa_score,
        "variants": saved_variants
    }


@router.post("/v1/content/{variant_id}/approve", response_model=ApprovalResponse)
def approve_content_variant(
    variant_id: str,
    req: ApprovalRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    try:
        approval = repo.record_approval(
            variant_id=variant_id,
            decision=req.decision,
            reviewer_id=user.user_id,
            workspace_id=user.workspace_id,
            feedback=req.feedback,
            edited_payload=req.edited_payload
        )
        variant = repo.db.query(ContentVariantModel).filter(ContentVariantModel.id == variant_id).first()
        
        # Record HITL human approval score in Langfuse
        score_val = 1.0 if req.decision == "approve" else (0.5 if req.decision in ("rewrite", "edit") else 0.0)
        ObservabilityTracer.record_score(
            name="human_approval",
            value=score_val,
            trace_id=variant.package_id if variant else variant_id,
            comment=f"Decision: {req.decision}. Feedback: {req.feedback or 'N/A'}"
        )

        return ApprovalResponse(
            id=approval.id,
            variant_id=approval.variant_id,
            decision=approval.decision,
            reviewer_id=approval.reviewer_id,
            payload_hash=approval.payload_hash,
            status_result=ContentStatus(variant.status if variant else ContentStatus.APPROVED),
            reviewed_at=approval.reviewed_at
        )
    except ValueError as e:
        if "access denied" in str(e).lower() or "not found" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/v1/inbox")
def get_review_inbox(
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    """Fetches all items awaiting human review in caller's workspace (IN_REVIEW status)."""
    pending = repo.get_inbox_variants(user.workspace_id)
    return [
        {
            "id": v.id,
            "package_id": v.package_id,
            "platform": v.platform,
            "hook": v.hook,
            "body": v.body,
            "cta": v.cta,
            "hashtags": v.hashtags,
            "media_spec": v.media_spec,
            "claims": v.claims,
            "payload_hash": v.payload_hash,
            "status": v.status,
            "created_at": v.created_at
        }
        for v in pending
    ]
