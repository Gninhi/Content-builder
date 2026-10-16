#!/usr/bin/env python3
"""
CLI interactif pour tester chaque agent / graphe de DeepAgent séparément.

Usage:
    python scripts/try_agent.py                     # Menu interactif
    python scripts/try_agent.py --agent <nom>        # Tester un agent spécifique
    python scripts/try_agent.py --list               # Lister les agents disponibles
    python scripts/try_agent.py --all                # Tester tous les agents séquentiellement
"""

import sys
import time
import argparse
from pathlib import Path

# Assurer le chargement des variables d'environnement
from dotenv import load_dotenv
load_dotenv(".env", override=True)

# Ajouter la racine du projet au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash


def print_banner(title: str):
    width = 70
    print("\n" + "=" * width)
    print(f"  🤖 AGENT : {title.upper()}")
    print("=" * width)


def test_idea_research():
    print_banner("1. Idea Research (Idéation & Veille)")
    print("ℹ️ Nœuds : collect_sources ➔ ideate_and_score")
    print("⏳ Exécution de la collecte et génération des idées...")
    
    from services.orchestration.graphs.idea_research import graph
    
    payload = {
        "workspace_id": "ws_demo",
        "topic_or_brief": "Gouvernance et Orchestration des Agents IA en Production",
        "pillars": ["IA générative", "Orchestration", "Gouvernance"],
        "audience": ["Tech Leads", "Architectes Logiciels"],
        "target_count": 2,
        "raw_sources": [
            {
                "url": "https://arxiv.org/abs/2401.00001",
                "title": "Architectures Multi-Agents pour l'Entreprise",
                "content": "Protocoles de gouvernance, consensus déterministe et observabilité pour les agents autonomes."
            }
        ],
        "generated_ideas": [],
        "run_id": f"run_idea_{int(time.time())}",
        "errors": []
    }
    
    t0 = time.time()
    result = graph.invoke(payload)
    elapsed = time.time() - t0
    
    ideas = result.get("generated_ideas", [])
    print(f"\n✅ {len(ideas)} Idées générées en {elapsed:.2f}s :")
    for idx, idea in enumerate(ideas, 1):
        print(f"\n  [{idx}] {idea.get('title')}")
        print(f"      • Angle     : {idea.get('angle')}")
        print(f"      • Nouveauté : {idea.get('novelty_score')}/100")
        print(f"      • Pertinence: {idea.get('relevance_score')}/100")
        print(f"      • Risques   : {', '.join(idea.get('risks', [])) or 'Aucun'}")
    return result


def test_content_production():
    print_banner("2. Content Production (Génération Multi-Plateforme)")
    print("ℹ️ Nœuds : generate_variants ➔ quality_gate")
    print("⏳ Génération des déclinaisons LinkedIn et X avec validation QA...")
    
    from services.orchestration.graphs.content_production import graph
    
    payload = {
        "workspace_id": "ws_demo",
        "brief_id": "brief_42",
        "objective": "Démontrer la valeur du Human-in-the-Loop pour fiabiliser les agents",
        "angle": "Cas réel de dérive évitée grâce à une validation humaine",
        "target_platforms": ["linkedin", "x"],
        "brand_voice": "Direct, expert, pragmatique",
        "prohibited_topics": ["crypto", "conseil financier"],
        "cta_policy": {"allowed_ctas": ["Partagez votre avis en commentaire"]},
        "sources": [
            {
                "canonical_url": "https://deepagent.internal/case-study",
                "facts": ["L'intervention humaine avant publication supprime 100% des erreurs critiques."]
            }
        ],
        "requirements": {},
        "generated_variants": [],
        "qa_results": {},
        "status": ContentStatus.DRAFT,
        "run_id": f"run_prod_{int(time.time())}",
        "errors": []
    }
    
    t0 = time.time()
    result = graph.invoke(payload)
    elapsed = time.time() - t0
    
    variants = result.get("generated_variants", [])
    print(f"\n✅ {len(variants)} Variantes générées en {elapsed:.2f}s (Statut: {result.get('status')}):")
    for v in variants:
        print(f"\n  --- Plateforme : {v.get('platform').upper()} (Score QA: {v.get('qa_score')}/100) ---")
        print(f"  Hook : {v.get('hook')}")
        print(f"  Body :\n{v.get('body')}")
        print(f"  CTA  : {v.get('cta')}")
    return result


def test_quality_review():
    print_banner("3. Quality Review (Quality Gate & Vérifications Déterministes)")
    print("ℹ️ Nœud : quality_gate")
    print("⏳ Analyse de conformité d'une variante de contenu...")
    
    from services.orchestration.graphs.quality_review import graph
    
    payload = {
        "workspace_id": "ws_demo",
        "brief_id": "brief_demo",
        "objective": "Vérification QA",
        "angle": "Audit",
        "target_platforms": ["linkedin"],
        "brand_voice": "Expert",
        "prohibited_topics": ["crypto"],
        "cta_policy": {},
        "sources": [],
        "requirements": {},
        "generated_variants": [
            {
                "platform": "linkedin",
                "hook": "L'orchestration d'agents LLM nécessite une rigueur d'ingénierie absolue.",
                "body": "Déployer des modèles sans barrières de sécurité expose à des dérives sévères. Une architecture stateful avec un moteur de règles déterministes permet de garantir la conformité sans sacrifier l'agilité.",
                "cta": "Partagez votre retour d'expérience en commentaire.",
                "claims": [],
                "media_spec": {}
            }
        ],
        "qa_results": {},
        "status": ContentStatus.DRAFT,
        "run_id": "run_qa_test",
        "errors": []
    }
    
    t0 = time.time()
    result = graph.invoke(payload)
    elapsed = time.time() - t0
    
    v = result["generated_variants"][0]
    print(f"\n✅ Contrôle terminé en {elapsed:.2f}s :")
    print(f"  • Score global  : {v.get('qa_score')}/100")
    print(f"  • Statut final  : {v.get('status')}")
    print(f"  • Règle validée : {v.get('qa_passed')}")
    print("\n  Détail des 6 règles vérifiées :")
    for check in v.get("checks", []):
        mark = "✅" if check["passed"] else "❌"
        print(f"    {mark} [{check['rule_id']}] {check['name']} : {check['details']}")
    return result


def test_approval():
    print_banner("4. Approval (Human-in-the-Loop & Signature Cryptographique)")
    print("ℹ️ Nœuds : prepare_for_review ➔ [INTERRUPTION HITL] ➔ human_review")
    print("⏳ Étape 1 : Exécution jusqu'au point d'arrêt humain...")
    
    from services.orchestration.graphs.approval import graph
    
    raw_payload = {
        "platform": "linkedin",
        "hook": "Voici pourquoi le HITL est le premier rempart en production.",
        "body": "Aucune publication ne doit être autorisée sans validation explicite d'un réviseur.",
        "cta": "Qu'en pensez-vous ?"
    }
    p_hash = compute_payload_hash(raw_payload)
    thread_id = f"thread_demo_{int(time.time())}"
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "variant_id": "var_hitl_01",
        "package_id": "pkg_hitl_01",
        "payload": raw_payload,
        "payload_hash": p_hash,
        "decision": None,
        "reviewer_id": None,
        "feedback": None,
        "status": ContentStatus.IN_REVIEW
    }
    
    # 1. Exécution jusqu'à l'interruption
    graph.invoke(initial_state, config=config)
    snapshot = graph.get_state(config)
    print(f"  ⏸️ Interruption déclenchée avec succès avant : {snapshot.next}")
    print(f"  🔒 Sceau SHA-256 calculé : {p_hash[:24]}...")
    
    # 2. Simulation de la décision humaine
    print("\n⏳ Étape 2 : L'opérateur humain valide le contenu...")
    decision = {
        "decision": "approve",
        "reviewer_id": "editeur_martial",
        "feedback": "Validé conforme au ton de la marque."
    }
    graph.update_state(config, decision)
    
    # 3. Reprise
    print("⏳ Étape 3 : Reprise du graphe après approbation...")
    final = graph.invoke(None, config=config)
    print("\n✅ Graphe terminé :")
    print(f"  • Décision humaine enregistrée : {final.get('decision')}")
    print(f"  • Réviseur                    : {final.get('reviewer_id')}")
    print(f"  • Statut final                : {final.get('status')}")
    return final


def test_scheduling():
    print_banner("5. Scheduling (Planification & Calendrier Éditorial)")
    print("ℹ️ Nœud : schedule_job")
    print("⏳ Attribution d'un créneau et verrou d'idempotence...")
    
    from services.orchestration.graphs.scheduling import graph
    
    payload = {
        "workspace_id": "ws_demo",
        "variant_id": "var_demo_01",
        "platform": "linkedin",
        "scheduled_at": "2026-10-15T09:00:00Z",
        "idempotency_key": f"key_sched_{int(time.time())}",
        "status": ContentStatus.SCHEDULED,
        "job_id": None,
        "error": None
    }
    
    t0 = time.time()
    result = graph.invoke(payload)
    elapsed = time.time() - t0
    
    print(f"\n✅ Job planifié en {elapsed:.2f}s :")
    print(f"  • Statut           : {result.get('status')}")
    print(f"  • ID de Job généré : {result.get('job_id')}")
    print(f"  • Date prévue      : {result.get('scheduled_at')}")
    print(f"  • Clé idempotence  : {result.get('idempotency_key')}")
    return result


def test_publishing():
    print_banner("6. Publishing (Publication Déterministe & Reçu Infalsifiable)")
    print("ℹ️ Nœud : verify_and_publish (Sandbox Mode)")
    print("⏳ Contrôle d'intégrité du hash et publication sécurisée...")
    
    from services.orchestration.graphs.publishing import graph
    
    post_content = {
        "platform": "linkedin",
        "hook": "L'automatisation sans dérive.",
        "body": "Post prêt pour diffusion certifiée."
    }
    valid_hash = compute_payload_hash(post_content)
    
    payload = {
        "job_id": f"job_pub_{int(time.time())}",
        "variant_id": "var_demo_01",
        "platform": "linkedin",
        "payload": post_content,
        "idempotency_key": f"idemp_{int(time.time())}",
        "approval_hash": valid_hash,
        "status": "ready",
        "receipt": None,
        "error": None
    }
    
    t0 = time.time()
    result = graph.invoke(payload)
    elapsed = time.time() - t0
    
    receipt = result.get("receipt", {})
    print(f"\n✅ Publication exécutée en {elapsed:.2f}s :")
    print(f"  • Statut           : {result.get('status')}")
    print(f"  • Reçu externe ID  : {receipt.get('external_id')}")
    print(f"  • Permalink        : {receipt.get('permalink')}")
    print(f"  • Mode Sandbox     : {receipt.get('sandbox')}")
    return result


def test_analytics():
    print_banner("7. Analytics (Normalisation des Métriques Multi-Canal)")
    print("ℹ️ Nœud : normalize_metrics")
    print("⏳ Calcul des taux d'engagement et indices de performance...")
    
    from services.orchestration.graphs.analytics import graph
    
    payload = {
        "post_id": "post_li_8832",
        "platform": "linkedin",
        "time_window": "7d",
        "raw_metrics": {
            "impressions": 4820,
            "likes": 215,
            "comments": 42,
            "shares": 19,
            "clicks": 180
        },
        "normalized_metrics": {},
        "status": "pending"
    }
    
    t0 = time.time()
    result = graph.invoke(payload)
    elapsed = time.time() - t0
    
    norm = result.get("normalized_metrics", {})
    print(f"\n✅ Métriques normalisées en {elapsed:.2f}s :")
    print(f"  • Impressions        : {norm.get('impressions')}")
    print(f"  • Taux d'engagement  : {norm.get('engagement_rate_pct')}%")
    print(f"  • Taux de clic (CTR) : {norm.get('click_through_rate_pct')}%")
    print(f"  • Amplification      : {norm.get('amplification_rate_pct')}%")
    print(f"  • Indice global      : {norm.get('performance_index')}/100")
    return result


def test_strategy_insights():
    print_banner("8. Strategy Insights (Génération de Recommandations Stratégiques)")
    print("ℹ️ Nœud : generate_insights")
    print("⏳ Analyse des métriques agrégées et synthèse de recommandations...")
    
    from services.orchestration.graphs.strategy_insights import graph
    
    payload = {
        "workspace_id": "ws_demo",
        "pillars": ["IA générative & LLMs", "Observabilité & HITL", "Architecture logicielle"],
        "metric_snapshots": [
            {"pillar": "IA générative & LLMs", "reach": 12500, "engagement_rate": 0.062},
            {"pillar": "Observabilité & HITL", "reach": 8900, "engagement_rate": 0.078},
            {"pillar": "Architecture logicielle", "reach": 4200, "engagement_rate": 0.021}
        ],
        "hypotheses": [],
        "recommendations": [],
        "confidence_levels": {},
        "status": "pending"
    }
    
    t0 = time.time()
    result = graph.invoke(payload)
    elapsed = time.time() - t0
    
    recs = result.get("recommendations", [])
    print(f"\n✅ {len(recs)} Recommandations formulées en {elapsed:.2f}s :")
    for r in recs:
        print(f"  • [{r.get('id')}] {r.get('title')}")
        print(f"    Impact attendu : {r.get('expected_impact')}")
        print(f"    Statut         : {r.get('status')}")
    return result


AGENTS = {
    "idea_research": ("Idéation & Veille multi-sources", test_idea_research),
    "content_production": ("Génération de variantes de contenu", test_content_production),
    "quality_review": ("Contrôle qualité déterministe (Quality Gate)", test_quality_review),
    "approval": ("Validation humaine (Human-in-the-Loop)", test_approval),
    "scheduling": ("Planification dans le calendrier", test_scheduling),
    "publishing": ("Publication déterministe sécurisée", test_publishing),
    "analytics": ("Normalisation des métriques", test_analytics),
    "strategy_insights": ("Recommandations stratégiques", test_strategy_insights),
}


def interactive_menu():
    while True:
        print("\n" + "=" * 60)
        print("    🚀 TESTEUR D'AGENTS INDIVIDUELS - DEEPAGENT")
        print("=" * 60)
        keys = list(AGENTS.keys())
        for idx, key in enumerate(keys, 1):
            desc, _ = AGENTS[key]
            print(f"  [{idx}] {key:<20} : {desc}")
        print("  [A] TOUS LES AGENTS      : Exécuter la suite complète")
        print("  [Q] Quitter")
        print("=" * 60)
        
        choice = input("\nChoisissez un agent à tester (1-8, A, Q) : ").strip().lower()
        if choice == "q":
            print("\nAu revoir !")
            break
        elif choice == "a":
            for name, (_, func) in AGENTS.items():
                try:
                    func()
                except Exception as e:
                    print(f"\n❌ Erreur sur {name} : {e}")
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            selected_key = keys[int(choice) - 1]
            _, func = AGENTS[selected_key]
            try:
                func()
            except Exception as e:
                print(f"\n❌ Erreur sur {selected_key} : {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Choix invalide, veuillez réessayer.")


def main():
    parser = argparse.ArgumentParser(description="Tester chaque agent de DeepAgent séparément.")
    parser.add_argument("--agent", choices=list(AGENTS.keys()), help="Nom de l'agent à exécuter")
    parser.add_argument("--list", action="store_true", help="Lister tous les agents disponibles")
    parser.add_argument("--all", action="store_true", help="Exécuter tous les agents séquentiellement")
    args = parser.parse_args()

    if args.list:
        print("\nAgents disponibles :")
        for k, (desc, _) in AGENTS.items():
            print(f"  • {k:<20} - {desc}")
        sys.exit(0)

    if args.all:
        for name, (_, func) in AGENTS.items():
            try:
                func()
            except Exception as e:
                print(f"❌ Erreur sur {name} : {e}")
        sys.exit(0)

    if args.agent:
        _, func = AGENTS[args.agent]
        func()
        sys.exit(0)

    # Mode interactif par défaut
    interactive_menu()


if __name__ == "__main__":
    main()
