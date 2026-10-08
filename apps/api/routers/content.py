from typing import cast, Dict, Any
from datetime import datetime
from langchain_core.runnables import RunnableConfig
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
from packages.domain.idempotency import compute_payload_hash
from services.orchestration.llm import get_gemini_model, GeneratedVariant

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
    if brief.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Access to brief belonging to another workspace is forbidden.")

    workspace_id = str(brief.workspace_id)
    brand_profile = repo.get_latest_brand_profile(workspace_id)
    voice = str(brand_profile.voice) if brand_profile else "Expert et direct"
    prohibited = list(brand_profile.prohibited_topics) if brand_profile else []
    cta_policy = dict(brand_profile.cta_policy) if brand_profile and brand_profile.cta_policy else {}

    sources = repo.list_sources(workspace_id)
    raw_sources = [
        {"canonical_url": s.canonical_url, "facts": s.extracted_facts}
        for s in sources
    ]

    initial_state = {
        "workspace_id": workspace_id,
        "brief_id": str(brief.id),
        "objective": str(brief.objective),
        "angle": "Perspective d'expert et retour terrain",
        "target_platforms": list(brief.platform_targets) if brief.platform_targets else ["linkedin", "x"],
        "brand_voice": voice,
        "prohibited_topics": prohibited,
        "cta_policy": cta_policy,
        "require_ai_disclosure": bool(cta_policy.get("require_ai_disclosure", False)),
        "sources": raw_sources,
        "requirements": dict(brief.requirements) if brief.requirements else {},
        "generated_variants": [],
        "qa_results": {},
        "status": ContentStatus.DRAFT,
        "run_id": "run_prod_1",
        "errors": []
    }

    # Run LangGraph content production and quality gate workflow with Langfuse tracing
    callback = ObservabilityTracer.get_callback_handler()
    config: RunnableConfig = cast(RunnableConfig, {"callbacks": [callback]} if callback else {})
    exec_result = cast(Dict[str, Any], content_production_graph.invoke(cast(Any, initial_state), config=config))

    qa_info = exec_result.get("qa_results", {})
    package_status = exec_result.get("status", ContentStatus.DRAFT)

    package = repo.create_content_package(
        brief_id=str(brief.id),
        version=1,
        model_metadata={"orchestrator": "LangGraph", "voice": voice},
        qa_score=float(qa_info.get("overall_score", 90.0))
    )
    setattr(package, "status", package_status.value)
    repo.db.commit()

    # Record QA gate evaluation score in Langfuse
    ObservabilityTracer.record_score(
        name="qa_gate_score",
        value=float(qa_info.get("overall_score", 90.0)) / 100.0,
        trace_id=str(package.id),
        comment=f"Deterministic and semantic QA evaluation for package {package.id}"
    )

    saved_variants = []
    for var in exec_result.get("generated_variants", []):
        variant_model = repo.add_variant(
            package_id=str(package.id),
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
            trace_id=str(variant.package_id) if variant else str(variant_id),
            comment=f"Decision: {req.decision}. Feedback: {req.feedback or 'N/A'}"
        )

        return ApprovalResponse(
            id=str(approval.id),
            variant_id=str(approval.variant_id),
            decision=str(approval.decision),
            reviewer_id=str(approval.reviewer_id),
            payload_hash=str(approval.payload_hash),
            status_result=ContentStatus(str(variant.status) if variant else ContentStatus.APPROVED.value),
            reviewed_at=cast(datetime, approval.reviewed_at)
        )
    except ValueError as e:
        if "access denied" in str(e).lower() or "not found" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/v1/content/{variant_id}/rewrite")
def rewrite_content_variant(
    variant_id: str,
    feedback: str = Body(..., embed=True),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    """
    Triggers an intelligent agent rewrite of the specified content variant based on human reviewer feedback.
    Applies real LLM / Gemini refinement, updates variant body & hook, and re-calculates cryptographic hash.
    """
    variant = repo.db.query(ContentVariantModel).filter(ContentVariantModel.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found.")

    package = variant.package
    brief = package.brief if package else None
    if brief and brief.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Forbidden workspace access.")

    # Record the feedback approval
    repo.record_approval(
        variant_id=variant_id,
        decision="rewrite",
        reviewer_id=user.user_id,
        workspace_id=user.workspace_id,
        feedback=feedback
    )

    # Invoke Gemini / LLM to rewrite based on user feedback
    model = get_gemini_model(model_type="reasoning", temperature=0.3)
    revised_hook: str = str(variant.hook or "")
    revised_body: str = str(variant.body or "")
    revised_cta: str = str(variant.cta or "")

    if model is not None:
        try:
            prompt = f"""Tu es un expert éditorial ContentOps de haut niveau.
L'utilisateur a examiné le post {variant.platform} suivant et a formulé ce retour critique à intégrer impérativement :
FEEDBACK DU RELECTEUR : "{feedback}"

POST ACTUEL :
Accroche (Hook) : {variant.hook}
Corps (Body) : {variant.body}
Call to Action (CTA) : {variant.cta}

Mission : Réécris ce post en intégrant scrupuleusement le feedback du relecteur.
Garde le style professionnel et direct. Ne génère aucune hallucination."""
            structured_llm = model.with_structured_output(GeneratedVariant)
            res = structured_llm.invoke(prompt)
            if res and res.body:
                revised_hook = str(res.hook or "")
                revised_body = str(res.body or "")
                revised_cta = str(res.cta or variant.cta or "")
        except Exception:
            revised_body = f"{variant.body}\n\n[Révision suite au retour : {feedback}]"
    else:
        revised_body = f"{variant.body}\n\n[Révision suite au retour : {feedback}]"

    # Update variant with revised content and recalculate payload hash
    new_payload: Dict[str, Any] = {
        "hook": revised_hook,
        "body": revised_body,
        "cta": revised_cta,
        "hashtags": variant.hashtags or [],
        "media_spec": variant.media_spec or {},
        "claims": variant.claims or []
    }
    new_hash = compute_payload_hash(new_payload)

    setattr(variant, "hook", revised_hook)
    setattr(variant, "body", revised_body)
    setattr(variant, "cta", revised_cta)
    setattr(variant, "payload_hash", new_hash)
    setattr(variant, "status", ContentStatus.IN_REVIEW.value)
    repo.db.commit()
    repo.db.refresh(variant)

    return {
        "status": "REWRITTEN",
        "variant_id": variant.id,
        "hook": variant.hook,
        "body": variant.body,
        "cta": variant.cta,
        "payload_hash": variant.payload_hash,
        "message": "Le brouillon a été réécrit avec succès par l'agent en intégrant votre retour !"
    }



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
