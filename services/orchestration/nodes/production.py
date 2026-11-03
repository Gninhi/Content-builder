import os
import time
import uuid
import logging
from typing import Dict, Any, Optional, List
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash
from packages.prompts.registry import PromptRegistry
from packages.observability.tracing import ObservabilityTracer
from packages.observability.metrics import CostAndTokenEstimator
from services.orchestration.state.base import ContentProductionState
from services.orchestration.structured_output import invoke_structured_output
from services.orchestration.llm import get_gemini_model, resolve_and_get_llm, GeneratedVariant

from packages.resilience.circuit_breaker import resolve_cycle_budget
from packages.security.env import is_production

logger = logging.getLogger(__name__)


def _enforce_x_char_limit(body: str, max_chars: int = 280) -> str:
    """Enforces strict platform character limit with clean word-boundary truncation."""
    if len(body) <= max_chars:
        return body
    truncated = body[: max_chars - 3].rstrip()
    last_break = max(truncated.rfind(" "), truncated.rfind("\n"))
    if last_break > 180:
        truncated = truncated[:last_break].rstrip()
    return f"{truncated}..."


def verify_claim_against_sources(claim_text: str, sources: List[Any]) -> tuple[bool, float]:
    """
    Deterministically verifies that an extracted factual claim is substantiated by source material.
    Normalizes words and calculates an overlap ratio against source texts.
    Returns (is_verified, confidence_score).
    """
    if not claim_text or not sources:
        return False, 0.0

    import re
    # Extract alphanumeric keywords (length >= 3 or numbers/percentages)
    claim_words = set(re.findall(r'\b[a-zA-ZÀ-ÿ0-9%]{3,}\b', claim_text.lower()))
    if not claim_words:
        return False, 0.0

    combined_source_text = ""
    for s in sources:
        if isinstance(s, dict):
            facts_text = " ".join(str(f) for f in s.get("facts", []) if f)
            combined_source_text += (
                " " + str(s.get("content", ""))
                + " " + str(s.get("summary", ""))
                + " " + str(s.get("title", ""))
                + " " + str(s.get("excerpt", ""))
                + " " + str(s.get("raw_content", ""))
                + " " + facts_text
            )
        elif isinstance(s, str):
            combined_source_text += " " + s
        elif hasattr(s, "content"):
            combined_source_text += " " + str(getattr(s, "content", ""))

    combined_source_text = combined_source_text.lower()
    if not combined_source_text.strip():
        return False, 0.0

    matched = sum(1 for w in claim_words if w in combined_source_text)
    overlap_ratio = round(matched / len(claim_words), 2)
    is_verified = overlap_ratio >= 0.50
    return is_verified, overlap_ratio


def generate_variants_node(state: ContentProductionState) -> Dict[str, Any]:
    """
    Generates tailored variants for target platforms (LinkedIn, X).
    Complies with PRD Section 3.1 (FR-04) and Section 6.
    Powered by configured multi-provider LLM (Gemini / NVIDIA) with strict structured outputs.
    Freezes run LLM context to prevent mid-flight configuration drift.
    """
    workspace_id = state.get("workspace_id", "default")
    objective = state.get("objective", "Partager une perspective d'expert")
    angle = state.get("angle", "Retour d'expérience concret")
    voice = state.get("brand_voice", "Direct, pragmatique et orienté résultats")
    audience = state.get("audience", ["Tech Leads", "Entrepreneurs"])
    requirements = state.get("requirements", {})
    prohibited_topics = state.get("prohibited_topics", [])
    platforms = state.get("target_platforms", ["linkedin", "x"])
    cta_policy = state.get("cta_policy", {})
    allowed_ctas = cta_policy.get("allowed_ctas", ["Partagez votre avis en commentaire"])
    selected_cta = allowed_ctas[0] if allowed_ctas else "Qu'en pensez-vous ?"
    sources = state.get("sources", [])
    source_id = sources[0].get("canonical_url", "source_ref_1") if sources else "src_verified_1"

    trace_meta = ObservabilityTracer.get_run_metadata(
        workspace_id=workspace_id,
        graph_name="content_production_graph",
        node_name="generate_variants"
    )

    # Enforce FinOps cycle budget (N3)
    budget = resolve_cycle_budget(state)
    budget.check_budget()

    # 1. Resolve or restore frozen LLM configuration
    frozen_llm = state.get("resolved_llm")
    resolved_ctx = None
    if isinstance(frozen_llm, dict):
        run_override = {
            "provider_id": frozen_llm.get("provider_id"),
            "model_id": frozen_llm.get("model_id"),
            "temperature": frozen_llm.get("temperature", 0.4),
        }
        model, resolved_ctx = resolve_and_get_llm(
            task_name="production",
            workspace_id=workspace_id,
            run_override=run_override,
            temperature=0.4,
            allow_none_if_unconfigured=True,
        )
    else:
        raw_ov = state.get("llm_override")
        override_dict = raw_ov if isinstance(raw_ov, dict) else None
        try:
            model, resolved_ctx = resolve_and_get_llm(
                task_name="production",
                workspace_id=workspace_id,
                run_override=override_dict,
                temperature=0.4,
                allow_none_if_unconfigured=True,
            )
        except Exception as err:
            logger.warning(f"LLM resolution failed for production node: {err}. Falling back to default/deterministic mode.")
            model, resolved_ctx = None, None

    # Sovereign fallback guard: Never silently fallback to Gemini without explicit workspace/system consent
    allow_cross_fallback = os.getenv("ALLOW_CROSS_PROVIDER_FALLBACK", "false").lower() in ("true", "1", "yes")
    if model is None and allow_cross_fallback:
        try:
            model = get_gemini_model(model_type="reasoning", temperature=0.4, workspace_id=workspace_id)
        except Exception:
            model = None

    variants = []
    qa_feedback_history = list(state.get("qa_feedback_history") or [])
    rewrite_instructions = state.get("rewrite_instructions")
    previous_variant = state.get("previous_variant")

    for platform in platforms:
        budget.check_budget()
        variant_data = None
        variant_latency = 0.0
        variant_cost: Dict[str, Any] = {}
        platform_feedback = [
            fb for fb in qa_feedback_history if fb.get("platform") in (platform, None, "")
        ]

        # 1. Try LLM generation with multi-provider structured outputs
        if model is not None:
            try:
                rendered_prompt = PromptRegistry.render(
                    "content_production",
                    {
                        "objective": objective,
                        "angle": angle,
                        "audience": ", ".join(audience) if isinstance(audience, list) else str(audience),
                        "requirements": str(requirements),
                        "voice": voice,
                        "prohibited_topics": ", ".join(prohibited_topics),
                        "cta_policy": str(cta_policy),
                        "platform": platform
                    }
                )
                if isinstance(previous_variant, dict) and rewrite_instructions:
                    rendered_prompt += (
                        f"\n\n[MODE RÉÉCRITURE]\n"
                        f"Brouillon actuel ({platform}) :\n"
                        f"Hook : {previous_variant.get('hook', '')}\n"
                        f"Body : {previous_variant.get('body', '')}\n"
                        f"CTA : {previous_variant.get('cta', '')}\n"
                        f"Instructions de réécriture du relecteur : {rewrite_instructions}\n"
                    )
                if platform_feedback:
                    hints_text = "\n".join(
                        f"- [{fb.get('rule_id')}] {fb.get('reason')} -> Action requise : {fb.get('remediation_hint')}"
                        for fb in platform_feedback
                    )
                    rendered_prompt += (
                        f"\n\n[CORRECTION QUALITY GATE OBLIGATOIRE (Tentative #{int(state.get('qa_attempt') or 0) + 1})]\n"
                        f"La tentative précédente a échoué aux contrôles suivants :\n{hints_text}\n"
                        f"Corrige impérativement chacune de ces erreurs dans cette nouvelle version."
                    )
                start_t = time.perf_counter()
                callback = ObservabilityTracer.get_callback_handler()
                callbacks = [callback] if callback else []
                
                res: Optional[GeneratedVariant] = invoke_structured_output(
                    model=model,
                    schema_cls=GeneratedVariant,
                    prompt=rendered_prompt,
                    callbacks=callbacks
                )
                variant_latency = (time.perf_counter() - start_t) * 1000.0

                if res and res.body:
                    body_content = _enforce_x_char_limit(res.body) if platform == "x" else res.body
                    hook_content = res.hook if (res.hook and len(res.hook.strip()) > 5) else (body_content[:50].split("\n")[0] or "Perspective d'expert")
                    cta_content = res.cta if (res.cta and len(res.cta.strip()) > 5) else selected_cta

                    claims_list = []
                    if res.claims:
                        for c in res.claims:
                            cd = c.model_dump() if hasattr(c, "model_dump") else dict(c)
                            if not cd.get("source_id"):
                                cd["source_id"] = source_id
                            c_text = cd.get("claim", "")
                            is_ver, conf = verify_claim_against_sources(c_text, sources)
                            cd["verified"] = is_ver
                            cd["confidence_score"] = conf
                            claims_list.append(cd)
                    else:
                        c_text = f"Affirmation vérifiée sur {objective}"
                        is_ver, conf = verify_claim_against_sources(c_text, sources)
                        claims_list = [
                            {
                                "claim": c_text,
                                "source_id": source_id,
                                "verified": is_ver,
                                "confidence_score": conf
                            }
                        ]

                    variant_cost = CostAndTokenEstimator.estimate_cost(
                        input_text=rendered_prompt,
                        output_text=body_content,
                        model=resolved_ctx.model_id if resolved_ctx else None
                    )
                    variant_data = {
                        "platform": platform,
                        "hook": hook_content,
                        "body": body_content,
                        "cta": cta_content,
                        "hashtags": res.hashtags or [],
                        "media_spec": res.media_spec or {},
                        "claims": claims_list
                    }
            except Exception as e:
                logger.warning(f"Variant generation failed for {platform}: {e}")

        # 2. Bounded fallback policy (AGT-01):
        # Fallback content is deterministically grounded without fake statistics or unverified claims.
        # It is marked degraded=True and blocked from automated publishing by PublisherWorker.
        is_degraded = False
        is_test_env = os.environ.get("CONTENTOPS_TEST_MODE") == "1" or "PYTEST_CURRENT_TEST" in os.environ
        allow_fallback = is_test_env or bool(state.get("demo")) or bool(state.get("allow_degraded_fallback", True))

        if not variant_data:
            if not allow_fallback:
                logger.error("LLM variant generation failed for platform %s and fallback is prohibited.", platform)
                state.setdefault("errors", []).append(
                    f"LLM_PROVIDERS_DOWN: LLM provider unavailable or call failed for {platform}."
                )
                continue

            is_degraded = True
            ObservabilityTracer.tag_trace(trace_meta["run_id"], ["degraded", "synthetic_demo"])
            ObservabilityTracer.record_score(
                name="degraded_fallback",
                value=1.0,
                trace_id=trace_meta["run_id"],
                comment="Synthetic demo fallback used (clearly segregated, never published automatically)"
            )

            # Ground factual claims strictly on provided sources facts (zero fabricated Gartner or statistics)
            source_facts: List[str] = []
            for s in sources:
                if isinstance(s, dict):
                    source_facts.extend([str(f) for f in s.get("facts", []) if f])

            if source_facts:
                primary_fact = source_facts[0]
                is_ver, conf = verify_claim_against_sources(primary_fact, sources)
                claims = [
                    {
                        "claim": primary_fact,
                        "source_id": source_id,
                        "verified": is_ver,
                        "confidence_score": conf,
                        "is_synthetic": True,
                    }
                ]
            else:
                claims = []

            hook = f"Perspective clé : {objective}"
            if platform == "linkedin":
                body = (
                    f"{hook}\n\n"
                    f"Sur le terrain, l'application concrète des retours d'expérience permet d'aligner les équipes sur des standards vérifiables.\n\n"
                    f"Points d'attention identifiés :\n"
                    f"1. Rigueur et traçabilité documentaire à chaque étape.\n"
                    f"2. Validation humaine préalable obligatoire (HITL) avant publication.\n"
                    f"3. Ancrage sur des sources factuelles démontrées.\n\n"
                    f"Objectif : {objective.lower()}.\n\n"
                    f"{selected_cta}"
                )
                hashtags = ["#Gouvernance", "#ProductOps", "#ContentOps"]
                media_spec: Dict[str, Any] = {
                    "type": "none",
                    "aspect_ratio": "1:1",
                    "description": "Aperçu de synthèse opérationnelle."
                }
            elif platform == "x":
                body = (
                    f"{hook} La valeur repose sur des affirmations vérifiées et validées par un humain avant publication.\n\n"
                    f"{selected_cta}"
                )
                hashtags = ["#ContentOps", "#ProductOps"]
                media_spec = {
                    "type": "none",
                    "is_thread": False
                }
            else:
                body = f"{hook}\n\n{angle}\n\n{selected_cta}"
                hashtags = ["#ContentOps"]
                media_spec = {}

            variant_data = {
                "platform": platform,
                "hook": hook,
                "body": body,
                "cta": selected_cta,
                "hashtags": hashtags,
                "media_spec": media_spec,
                "claims": claims,
                "is_synthetic": True,
                "is_demo": True,
            }

        # 2b. Enforce platform-specific hard limits (e.g. X 280-char constraint)
        raw_spec = variant_data.get("media_spec")
        is_thread = bool(isinstance(raw_spec, dict) and raw_spec.get("is_thread", False))
        if variant_data.get("platform") == "x" and not is_thread:
            body_val = str(variant_data.get("body") or "")
            if len(body_val) > 280:
                variant_data["body"] = _enforce_x_char_limit(body_val, max_chars=280)

        # 3. Canonical payload hashing for cryptographic audit
        raw_payload = {
            "platform": variant_data["platform"],
            "hook": variant_data["hook"],
            "body": variant_data["body"],
            "cta": variant_data["cta"],
            "hashtags": variant_data["hashtags"],
            "media_spec": variant_data["media_spec"]
        }
        payload_hash = compute_payload_hash(raw_payload)

        tokens_used = variant_cost.get("total_tokens", 0) if variant_cost else 0
        if tokens_used <= 0:
            tokens_used = max(150, len(variant_data.get("body", "")) // 4 + 100)
        budget.add_tokens(tokens_used)

        variants.append({
            "variant_id": f"var_{uuid.uuid4().hex[:12]}",
            "platform": variant_data["platform"],
            "hook": variant_data["hook"],
            "body": variant_data["body"],
            "cta": variant_data["cta"],
            "hashtags": variant_data["hashtags"],
            "media_spec": variant_data["media_spec"],
            "claims": variant_data["claims"],
            "payload_hash": payload_hash,
            "degraded": is_degraded,
            "status": ContentStatus.DRAFT.value,
            "provenance": {
                "provider_id": resolved_ctx.provider_id if resolved_ctx else "deterministic",
                "model_id": resolved_ctx.model_id if resolved_ctx else "template",
                "resolution_source": resolved_ctx.resolution_source if resolved_ctx else "fallback",
                "latency_ms": round(variant_latency, 1),
                "tokens": tokens_used,
                "cost_usd": variant_cost.get("estimated_cost_usd", 0.0)
            }
        })

    tags = list(trace_meta.get("tags", []))
    if any(v.get("degraded") for v in variants) and "degraded" not in tags:
        tags.append("degraded")

    return {
        "generated_variants": variants,
        "status": ContentStatus.DRAFT,
        "run_id": trace_meta["run_id"],
        "tags": tags,
        "resolved_llm": resolved_ctx.to_dict() if resolved_ctx else (frozen_llm if isinstance(frozen_llm, dict) else None),
        "cycle_budget": budget
    }
