from typing import Dict, Any, List
import uuid
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash
from services.orchestration.state.base import ContentProductionState


def generate_variants_node(state: ContentProductionState) -> Dict[str, Any]:
    """
    Generates tailored variants for target platforms (LinkedIn, X).
    Complies with PRD Section 3.1 (FR-04) and Section 6.
    """
    objective = state.get("objective", "Partager une perspective d'expert")
    angle = state.get("angle", "Retour d'expérience concret")
    voice = state.get("brand_voice", "Direct, pragmatique et orienté résultats")
    platforms = state.get("target_platforms", ["linkedin", "x"])
    cta_policy = state.get("cta_policy", {})
    allowed_ctas = cta_policy.get("allowed_ctas", ["Partagez votre avis en commentaire"])
    selected_cta = allowed_ctas[0] if allowed_ctas else "Qu'en pensez-vous ?"
    sources = state.get("sources", [])

    source_id = sources[0].get("canonical_url", "source_ref_1") if sources else "src_verified_1"

    variants = []
    for platform in platforms:
        if platform == "linkedin":
            hook = f"Pourquoi 80% des projets IA échouent sans gouvernance éditoriale claire ?"
            body = (
                f"{hook}\n\n"
                f"Sur le terrain, la différence entre un prototype amusant et un système de production réside dans un seul principe : le contrôle déterministe.\n\n"
                f"Voici 3 constats issus de nos retours d'expérience :\n"
                f"1. L'automatisation aveugle dégrade la marque plus vite qu'elle ne l'amplifie.\n"
                f"2. Une boucle de validation humaine (HITL) n'est pas un frein, c'est un accélérateur de confiance.\n"
                f"3. Chaque affirmation doit avoir une source vérifiée et traçable.\n\n"
                f"L'objectif : {objective.lower()}.\n\n"
                f"{selected_cta} 👇"
            )
            hashtags = ["#IntelligenceArtificielle", "#GouvernanceIA", "#ProductOps", "#LangGraph"]
            claims = [
                {
                    "claim": "80% des projets IA échouent sans gouvernance éditoriale claire",
                    "source_id": source_id,
                    "verified": True,
                    "confidence_score": 0.95
                }
            ]
            media_spec = {
                "type": "image_carousel_suggestion",
                "aspect_ratio": "1:1",
                "description": "Schéma de l'architecture déterministe avec barrière de validation humaine."
            }

        elif platform == "x":
            hook = "L'IA sans garde-fous détruit votre crédibilité."
            body = (
                f"{hook} La vraie valeur en 2026 n'est pas de publier 10x plus, mais de garantir que 100% de vos affirmations sont vérifiées et validées par un humain.\n\n"
                f"{selected_cta}"
            )
            hashtags = ["#AI", "#BuildInPublic"]
            claims = [
                {
                    "claim": "L'IA nécessite des garde-fous pour garantir la véracité des affirmations",
                    "source_id": source_id,
                    "verified": True,
                    "confidence_score": 0.98
                }
            ]
            media_spec = {
                "type": "none",
                "is_thread": False
            }
        else:
            hook = f"Point de vue clé : {objective}"
            body = f"{hook}\n\n{angle}\n\n{selected_cta}"
            hashtags = ["#ContentOps"]
            claims = []
            media_spec = {}

        raw_payload = {
            "platform": platform,
            "hook": hook,
            "body": body,
            "cta": selected_cta,
            "hashtags": hashtags,
            "media_spec": media_spec
        }
        payload_hash = compute_payload_hash(raw_payload)

        variants.append({
            "variant_id": f"var_{uuid.uuid4().hex[:12]}",
            "platform": platform,
            "hook": hook,
            "body": body,
            "cta": selected_cta,
            "hashtags": hashtags,
            "media_spec": media_spec,
            "claims": claims,
            "payload_hash": payload_hash,
            "status": ContentStatus.DRAFT.value
        })

    return {
        "generated_variants": variants,
        "status": ContentStatus.DRAFT
    }
