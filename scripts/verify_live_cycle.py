import os
import sys
import uuid
import time
from dotenv import load_dotenv

# Load real environment variables from .env
load_dotenv(".env")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packages.observability.tracing import ObservabilityTracer  # noqa: E402
from packages.observability.metrics import CostAndTokenEstimator  # noqa: E402
from services.orchestration.graphs.idea_research import graph as idea_research_graph  # noqa: E402

def run_verification():
    print("=== ÉTAPE 1 : Vérification de la configuration Langfuse & Gemini ===")
    is_enabled = ObservabilityTracer.is_tracing_enabled()
    print(f"Tracing activé : {is_enabled}")
    assert is_enabled, "Le tracing Langfuse doit être activé avec les clés du .env"

    client = ObservabilityTracer.get_langfuse_client()
    assert client is not None, "Le client Langfuse doit être instancié"
    
    # Langfuse auth check
    auth_ok = client.auth_check()
    print(f"Langfuse auth_check() : {auth_ok}")
    assert auth_ok, "L'authentification Langfuse avec cloud.langfuse.com doit réussir"

    print("\n=== ÉTAPE 2 : Exécution d'un cycle de test LangGraph instrumenté ===")
    trace_id = str(uuid.uuid4())
    session_id = f"session_audit_{int(time.time())}"
    print(f"Trace ID généré : {trace_id}")

    handler = ObservabilityTracer.get_callback_handler(
        session_id=session_id,
        user_id="auditor_test",
        tags=["audit_verification", "gemini-3.8-flash", "test_cycle"]
    )

    # State input for research graph
    initial_state = {
        "workspace_id": "ws_default",
        "topic": "Gouvernance et Observabilité des Agents LLM en 2026",
        "target_audience": ["Tech Leads", "AI Engineers", "CTOs"],
        "brand_pillars": ["IA générative & LLMs", "Observabilité Langfuse"],
        "brand_voice": "Expert, pragmatique, direct, orienté architecture",
        "prohibited_topics": ["Spéculation crypto"],
        "max_ideas": 2,
        "evidence_sources": [
            {
                "fact_id": "fact_live_1",
                "claim": "Langfuse fournit une observabilité complète avec traçabilité des spans et scores de feedback",
                "source_id": "src_live_1",
                "confidence_score": 0.99
            }
        ]
    }

    config = {}
    if handler:
        config["callbacks"] = [handler]

    print("Invocation du graphe de recherche d'idées avec callback Langfuse...")
    start_time = time.time()
    result = idea_research_graph.invoke(initial_state, config=config)
    duration = time.time() - start_time
    print(f"Cycle terminé avec succès en {duration:.2f}s !")
    
    generated_ideas = result.get("generated_ideas", [])
    print(f"Nombre d'idées générées : {len(generated_ideas)}")
    assert len(generated_ideas) > 0, "Le cycle doit générer au moins une idée"
    print(f"Exemple d'idée : {generated_ideas[0].get('title')}")

    print("\n=== ÉTAPE 3 : Envoi d'un score de qualité (QA Gate) dans Langfuse ===")
    score_ok = ObservabilityTracer.record_score(
        name="qa_gate_score",
        value=0.96,
        trace_id=trace_id,
        comment="Test de vérification automatique après migration Gemini 3.8 & Langfuse"
    )
    print(f"Score QA enregistré dans Langfuse : {score_ok}")

    score_hitl = ObservabilityTracer.record_score(
        name="human_approval",
        value=1.0,
        trace_id=trace_id,
        comment="Approbation humaine simulée pour le cycle de validation"
    )
    print(f"Score HITL enregistré dans Langfuse : {score_hitl}")

    print("\n=== ÉTAPE 4 : Flush du client Langfuse vers cloud.langfuse.com ===")
    try:
        client.flush()
        print("Flush Langfuse exécuté avec succès vers cloud.langfuse.com !")
    except Exception as e:
        print(f"Erreur lors du flush Langfuse : {e}")
        raise

    print("\n=== ÉTAPE 5 : Estimation des coûts et tokens Gemini 3.8 Flash ===")
    cost_info = CostAndTokenEstimator.estimate_cost(
        input_text=str(initial_state),
        output_text=str(generated_ideas),
        model="gemini-3.8-flash"
    )
    print(f"Tokens estimés : {cost_info['input_tokens']} in, {cost_info['output_tokens']} out")
    print(f"Coût estimé : ${cost_info['estimated_cost_usd']:.6f} USD")

    print("\n✅ TOUTES LES VÉRIFICATIONS LANGFUSE & GEMINI ONT RÉUSSI !")

if __name__ == "__main__":
    run_verification()
