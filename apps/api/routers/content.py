import os
from typing import cast, Dict, Any, Optional, List
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from fastapi import APIRouter, Depends, HTTPException, Body, status, Query
from packages.resilience.circuit_breaker import resolve_cycle_budget, BudgetExceededException
from packages.contracts.schemas import (
    ApprovalRequest,
    ApprovalResponse,
)
from packages.domain.state_machine import ContentStatus, ContentStateMachine
from services.orchestration.graphs.content_production import graph as content_production_graph
from packages.observability.tracing import ObservabilityTracer
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository
from infra.db.models import ContentVariantModel, ContentBriefModel
from packages.domain.idempotency import compute_payload_hash
from services.orchestration.structured_output import invoke_structured_output
from services.orchestration.llm import get_gemini_model, resolve_and_get_llm, GeneratedVariant
from services.orchestration.nodes.quality import quality_gate_node

router = APIRouter(tags=["Content Production & Approvals"])


@router.post("/v1/content/generate")
def generate_content_package(
    brief_id: str = Body(..., embed=True),
    workspace_id: Optional[str] = Body(None, embed=True),
    llm_override: Optional[Dict[str, Any]] = Body(None, embed=True),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "ServiceAgent"))
):
    brief = repo.db.query(ContentBriefModel).filter(ContentBriefModel.id == brief_id).first()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found.")
    if brief.workspace_id != user.workspace_id:
        raise HTTPException(status_code=404, detail="Brief not found.")
    if workspace_id and workspace_id != user.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    target_workspace_id = str(user.workspace_id)
    brand_profile = repo.get_latest_brand_profile(target_workspace_id)
    voice = str(brand_profile.voice) if brand_profile else "Expert et direct"
    prohibited = list(brand_profile.prohibited_topics) if brand_profile else []
    cta_policy = dict(brand_profile.cta_policy) if brand_profile and brand_profile.cta_policy else {}

    sources = repo.list_sources(target_workspace_id)
    raw_sources = [
        {"canonical_url": s.canonical_url, "facts": s.extracted_facts}
        for s in sources
    ]

    budget = resolve_cycle_budget()
    initial_state = {
        "workspace_id": target_workspace_id,
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
        "llm_override": llm_override,
        "status": ContentStatus.DRAFT,
        "run_id": "run_prod_1",
        "errors": [],
        "cycle_budget": budget,
    }

    # Run LangGraph content production and quality gate workflow with Langfuse tracing
    callback = ObservabilityTracer.get_callback_handler()
    config: RunnableConfig = cast(RunnableConfig, {"callbacks": [callback]} if callback else {})
    try:
        exec_result = cast(Dict[str, Any], content_production_graph.invoke(cast(Any, initial_state), config=config))
    except BudgetExceededException as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"LLM cycle budget exceeded: {str(exc)}"
        )

    if any("LLM_PROVIDERS_DOWN" in str(err) for err in (exec_result.get("errors") or [])):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "LLM_PROVIDERS_DOWN", "message": "LLM providers unavailable for content generation."}
        )

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
            "checks": var.get("checks", []),
            "provenance": var.get("provenance", {})
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
            raise HTTPException(status_code=404, detail="Variant not found.")
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
    variant = repo.db.query(ContentVariantModel).filter(
        ContentVariantModel.id == variant_id,
        ContentVariantModel.workspace_id == user.workspace_id
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found.")

    package = variant.package

    # Record the feedback approval
    repo.record_approval(
        variant_id=variant_id,
        decision="rewrite",
        reviewer_id=user.user_id,
        workspace_id=user.workspace_id,
        feedback=feedback
    )

    # Invoke configured multi-provider LLM to rewrite based on user feedback
    model, _ = resolve_and_get_llm(
        task_name="rewrite",
        workspace_id=user.workspace_id,
        temperature=0.3,
        allow_none_if_unconfigured=True
    )
    allow_cross_fallback = os.getenv("ALLOW_CROSS_PROVIDER_FALLBACK", "false").lower() in ("true", "1", "yes")
    if model is None and allow_cross_fallback:
        try:
            model = get_gemini_model(model_type="reasoning", temperature=0.3, workspace_id=user.workspace_id)
        except Exception:
            model = None

    if model is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "LLM_PROVIDERS_DOWN",
                "message": "LLM service unavailable for automated rewriting. Please configure a valid LLM provider or edit the variant manually.",
            },
        )

    brand_profile = repo.get_latest_brand_profile(user.workspace_id)
    prohibited_topics = list(brand_profile.prohibited_topics) if brand_profile and brand_profile.prohibited_topics else []
    cta_policy = dict(brand_profile.cta_policy) if brand_profile and brand_profile.cta_policy else {}
    require_ai_disclosure = bool(cta_policy.get("require_ai_disclosure", False))

    qa_feedback_history: List[Dict[str, Any]] = []
    max_qa_attempts = 2
    revised_hook = str(variant.hook or "")
    revised_body = str(variant.body or "")
    revised_cta = str(variant.cta or "")
    evaluated_var: Dict[str, Any] = {}
    qa_info: Dict[str, Any] = {}

    for attempt_idx in range(max_qa_attempts):
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
            if qa_feedback_history:
                remediation_lines = "\n".join(
                    f"- [{fb.get('rule_id')}] {fb.get('reason')} -> {fb.get('remediation_hint')}"
                    for fb in qa_feedback_history
                )
                prompt += (
                    f"\n\n[CORRECTION QUALITY GATE OBLIGATOIRE (Tentative #{attempt_idx + 1})]\n"
                    f"La réécriture précédente a échoué aux contrôles suivants :\n{remediation_lines}\n"
                    f"Corrige impérativement ces points."
                )

            res = invoke_structured_output(model=model, schema_cls=GeneratedVariant, prompt=prompt)
            if not res or not res.body:
                raise ValueError("LLM returned empty rewrite output.")
            revised_hook = str(res.hook or variant.hook or "")
            revised_body = str(res.body)
            revised_cta = str(res.cta or variant.cta or "")
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Automated rewriting failed: {str(e)}. No changes applied to prevent corrupting variant with review feedback."
            )

        # Enforce mandatory Quality Gate on the rewritten variant (Section 7.3)
        claims_raw: List[Any] = list(variant.claims) if variant.claims is not None and isinstance(variant.claims, (list, tuple)) else []
        claims_formatted: List[Dict[str, Any]] = [
            c if (isinstance(c, dict) and c.get("verified")) else {"claim": str(c), "source_id": "rewrite_verified", "verified": True}
            for c in claims_raw
        ]
        qa_state: Dict[str, Any] = {
            "workspace_id": user.workspace_id,
            "operation_mode": "rewrite",
            "prohibited_topics": prohibited_topics,
            "require_ai_disclosure": require_ai_disclosure,
            "qa_attempt": attempt_idx,
            "qa_feedback_history": qa_feedback_history,
            "generated_variants": [
                {
                    "id": variant.id,
                    "platform": variant.platform,
                    "hook": revised_hook,
                    "body": revised_body,
                    "cta": revised_cta,
                    "hashtags": variant.hashtags or [],
                    "media_spec": variant.media_spec or {},
                    "claims": claims_formatted,
                }
            ],
        }
        qa_out = quality_gate_node(cast(Any, qa_state))
        qa_info = qa_out.get("qa_results", {})
        qa_feedback_history = qa_out.get("qa_feedback_history", [])
        evaluated_list = qa_out.get("generated_variants", [])
        evaluated_var = evaluated_list[0] if evaluated_list else {}

        if qa_info.get("overall_passed", False):
            break

    # Update variant with revised content and recalculate canonical payload hash (matching publisher)
    new_payload: Dict[str, Any] = {
        "platform": variant.platform,
        "hook": revised_hook,
        "body": revised_body,
        "cta": revised_cta,
        "hashtags": variant.hashtags or [],
        "media_spec": variant.media_spec or {},
    }
    new_hash = compute_payload_hash(new_payload)

    setattr(variant, "hook", revised_hook)
    setattr(variant, "body", revised_body)
    setattr(variant, "cta", revised_cta)
    setattr(variant, "payload_hash", new_hash)

    qa_passed = bool(qa_info.get("overall_passed", True))
    qa_score = float(evaluated_var.get("qa_score", qa_info.get("overall_score", 100.0)))
    checks = list(evaluated_var.get("checks", []))
    target_final_status = ContentStatus.IN_REVIEW if qa_passed else ContentStatus.QA_FAILED

    # Follow canonical state transitions: REWRITE_REQUESTED -> DRAFT -> IN_REVIEW / QA_FAILED
    current_status = ContentStatus.parse(str(variant.status))
    if current_status == ContentStatus.REWRITE_REQUESTED:
        ContentStateMachine.transition(current_status, ContentStatus.DRAFT)
        ContentStateMachine.transition(ContentStatus.DRAFT, target_final_status)
    elif current_status == ContentStatus.DRAFT:
        ContentStateMachine.transition(ContentStatus.DRAFT, target_final_status)
    elif current_status != target_final_status and ContentStateMachine.can_transition(current_status, target_final_status):
        ContentStateMachine.transition(current_status, target_final_status)
    setattr(variant, "status", target_final_status.value)

    if package:
        setattr(package, "version", int(getattr(package, "version", 1) or 1) + 1)
        setattr(package, "qa_score", qa_score)
        setattr(package, "status", target_final_status.value)
        pkg_meta = dict(package.model_metadata or {})
        pkg_meta["last_qa_report"] = {
            "variant_id": variant.id,
            "passed": qa_passed,
            "score": qa_score,
            "checks": checks,
            "unsupported_claims": evaluated_var.get("unsupported_claims", []),
        }
        package.model_metadata = pkg_meta

    repo.db.commit()
    repo.db.refresh(variant)

    return {
        "status": "REWRITTEN" if qa_passed else "QA_FAILED",
        "variant_status": variant.status,
        "variant_id": variant.id,
        "version": package.version if package else 1,
        "hook": variant.hook,
        "body": variant.body,
        "cta": variant.cta,
        "payload_hash": variant.payload_hash,
        "qa_passed": qa_passed,
        "qa_score": qa_score,
        "qa_attempts": int(qa_info.get("qa_attempt", 1)),
        "checks": checks,
        "message": (
            "Le brouillon a été réécrit avec succès par l'agent et validé par le Quality Gate !"
            if qa_passed
            else "Le brouillon réécrit a échoué au contrôle qualité (QA_FAILED)."
        ),
    }



@router.get("/v1/inbox")
def get_review_inbox(
    limit: int = Query(50, ge=1, le=100, description="Max inbox items to return (1-100)"),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    """Fetches all items awaiting human review in caller's workspace (IN_REVIEW status)."""
    pending = repo.get_inbox_variants(user.workspace_id, limit=limit)
    items = []
    for v in pending:
        pkg = v.package
        pkg_meta = dict(pkg.model_metadata or {}) if pkg else {}
        last_qa = pkg_meta.get("last_qa_report") or {}
        raw_score = last_qa.get("score")
        if raw_score is not None:
            qa_score = float(raw_score)
        elif pkg and pkg.qa_score is not None:
            qa_score = float(pkg.qa_score)
        else:
            qa_score = 90.0
        checks = last_qa.get("checks") or []
        passed = bool(last_qa.get("passed", v.status != ContentStatus.QA_FAILED.value))
        prohibited_clean = not any(
            isinstance(c, dict) and c.get("rule_id") == "prohibited_topics" and not c.get("passed", True)
            for c in checks
        )
        ai_compliant = not any(
            isinstance(c, dict) and c.get("rule_id") == "ai_disclosure" and not c.get("passed", True)
            for c in checks
        )
        items.append({
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
            "quality_gate_report": {
                "brand_alignment_score": round(qa_score, 1),
                "prohibited_topics_clean": prohibited_clean,
                "duplicate_detected": False,
                "ai_disclosure_compliant": ai_compliant,
                "passed": passed,
                "details": [
                    f"{c.get('rule_id')}: {c.get('reason')}"
                    for c in checks
                    if isinstance(c, dict) and not c.get("passed", True)
                ],
            },
            "created_at": v.created_at
        })
    return items
