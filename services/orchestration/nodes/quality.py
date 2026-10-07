from typing import Dict, Any
import re
from packages.domain.state_machine import ContentStatus
from services.orchestration.state.base import ContentProductionState


def quality_gate_node(state: ContentProductionState) -> Dict[str, Any]:
    """
    Quality Gate validator combining deterministic rule enforcement and claim verification.
    Complies with PRD Section 3.1 (FR-04, FR-05) and Section 6 (Quality Gate).
    """
    variants = state.get("generated_variants", [])
    prohibited_topics = state.get("prohibited_topics", [])
    
    total_checks_passed = 0
    total_checks = 0
    evaluated_variants = []

    for variant in variants:
        platform = variant.get("platform", "linkedin")
        body = variant.get("body", "")
        hook = variant.get("hook", "")
        cta = variant.get("cta", "")
        claims = variant.get("claims", [])
        
        checks = []
        unsupported_claims = []

        # 1. Platform length check
        if platform == "x":
            is_thread = variant.get("media_spec", {}).get("is_thread", False)
            char_ok = is_thread or len(body) <= 280
            checks.append({
                "rule_id": "PLATFORM_LENGTH",
                "name": "X 280 Character Limit",
                "passed": char_ok,
                "details": f"Length is {len(body)} chars (Limit: 280)" if not char_ok else "Compliant length"
            })
        else:
            char_ok = len(body) <= 3000 and len(body) >= 50
            checks.append({
                "rule_id": "PLATFORM_LENGTH",
                "name": "LinkedIn Length Limits",
                "passed": char_ok,
                "details": f"Length is {len(body)} chars"
            })

        # 2. Hook and CTA presence
        has_hook = bool(hook and len(hook.strip()) > 5)
        has_cta = bool(cta and len(cta.strip()) > 5)
        checks.append({
            "rule_id": "MANDATORY_HOOK",
            "name": "Opening Hook Presence",
            "passed": has_hook,
            "details": "Hook present" if has_hook else "Missing introductory hook"
        })
        checks.append({
            "rule_id": "MANDATORY_CTA",
            "name": "Call to Action Presence",
            "passed": has_cta,
            "details": "CTA present" if has_cta else "Missing closing CTA"
        })

        # 3. Prohibited topics check
        violations = []
        body_lower = body.lower()
        for topic in prohibited_topics:
            if topic.lower() in body_lower:
                violations.append(topic)
        checks.append({
            "rule_id": "BRAND_PROHIBITED_TOPICS",
            "name": "Prohibited Topics Compliance",
            "passed": len(violations) == 0,
            "details": f"Violations detected: {', '.join(violations)}" if violations else "No prohibited topics found"
        })

        # 4. Verified claims check
        for c in claims:
            if not c.get("verified", False) or not c.get("source_id"):
                unsupported_claims.append(c.get("claim", "Unknown claim"))

        checks.append({
            "rule_id": "FACTUAL_CLAIMS_VERIFIED",
            "name": "Source Attribution for Claims",
            "passed": len(unsupported_claims) == 0,
            "details": f"Unsupported claims: {unsupported_claims}" if unsupported_claims else "All claims backed by sources"
        })

        # 5. Security & Prompt Injection sanitization check
        suspicious = bool(re.search(r'(?i)(ignore\s+instructions|system\s*:\s*you\s+are|<script)', body))
        checks.append({
            "rule_id": "SECURITY_INJECTION_DEFENSE",
            "name": "No Injected Instructions",
            "passed": not suspicious,
            "details": "Content is clean" if not suspicious else "Suspicious prompt injection pattern found"
        })

        # 6. EU AI Act Transparency (configurable per brand policy according to decision Q6)
        require_ai_disclosure = state.get("require_ai_disclosure", False)
        if require_ai_disclosure:
            from evals.evaluators.quality_evaluator import DeterministicQualityRules
            ai_ok, ai_msg = DeterministicQualityRules.check_ai_transparency(body, required=True)
            checks.append({
                "rule_id": "AI_ACT_TRANSPARENCY",
                "name": "AI Transparency Disclosure",
                "passed": ai_ok,
                "details": ai_msg
            })

        passed_count = sum(1 for c in checks if c["passed"])
        variant_score = round((passed_count / len(checks)) * 100, 1)
        is_variant_passed = passed_count == len(checks)

        variant["qa_score"] = variant_score
        variant["qa_passed"] = is_variant_passed
        variant["checks"] = checks
        variant["unsupported_claims"] = unsupported_claims
        
        # In PRD: If QA passes, status is IN_REVIEW (ready for human approval). If fails, QA_FAILED.
        variant["status"] = ContentStatus.IN_REVIEW.value if is_variant_passed else ContentStatus.QA_FAILED.value
        
        total_checks_passed += passed_count
        total_checks += len(checks)
        evaluated_variants.append(variant)

    overall_score = round((total_checks_passed / total_checks * 100), 1) if total_checks > 0 else 0.0
    overall_passed = all(v["qa_passed"] for v in evaluated_variants)

    return {
        "generated_variants": evaluated_variants,
        "qa_results": {
            "overall_passed": overall_passed,
            "overall_score": overall_score,
            "variants_evaluated": len(evaluated_variants)
        },
        "status": ContentStatus.IN_REVIEW if overall_passed else ContentStatus.QA_FAILED
    }
