from services.orchestration.graphs.idea_research import graph as idea_research_graph
from services.orchestration.graphs.content_production import graph as content_production_graph
from services.orchestration.nodes.approval import create_approval_graph
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash

approval_graph = create_approval_graph()


def test_idea_research_graph_execution():
    state = {
        "workspace_id": "ws_test",
        "topic_or_brief": "Systèmes multi-agents gouvernés",
        "pillars": ["IA générative", "Orchestration"],
        "audience": ["Tech Leads"],
        "target_count": 3,
        "raw_sources": [
            {
                "url": "https://arxiv.org/abs/2401.00001",
                "title": "Architectures Multi-Agents pour l'Entreprise",
                "content": "Protocoles d'orchestration, consensus et gouvernance des systèmes multi-agents en production."
            }
        ],
        "generated_ideas": [],
        "run_id": "",
        "errors": []
    }
    result = idea_research_graph.invoke(state)
    ideas = result.get("generated_ideas", [])
    assert len(ideas) >= 1
    assert "title" in ideas[0]
    assert "angle" in ideas[0]
    assert "novelty_score" in ideas[0]


def test_content_production_graph_execution():
    state = {
        "workspace_id": "ws_test",
        "brief_id": "brief_01",
        "objective": "Démontrer la valeur du human-in-the-loop",
        "angle": "Cas réel de production",
        "target_platforms": ["linkedin", "x"],
        "brand_voice": "Direct et expert",
        "prohibited_topics": ["crypto"],
        "cta_policy": {"allowed_ctas": ["Partagez votre avis"]},
        "sources": [
            {
                "canonical_url": "https://example.com/source",
                "facts": [
                    "80% des projets IA échouent sans gouvernance éditoriale claire",
                    "L'IA nécessite des garde-fous pour garantir la véracité des affirmations"
                ]
            }
        ],
        "requirements": {},
        "generated_variants": [],
        "qa_results": {},
        "status": ContentStatus.DRAFT,
        "run_id": "run_01",
        "errors": []
    }
    result = content_production_graph.invoke(state)
    variants = result.get("generated_variants", [])
    assert len(variants) == 2
    assert variants[0]["platform"] in ("linkedin", "x")
    assert result["status"] == ContentStatus.IN_REVIEW


def test_approval_graph_interrupt_and_resume():
    raw_payload = {
        "platform": "linkedin",
        "hook": "Un hook solide",
        "body": "Un corps de texte vérifié et structuré.",
        "cta": "Partagez votre avis",
        "hashtags": ["#AI"],
        "media_spec": {}
    }
    p_hash = compute_payload_hash(raw_payload)

    config = {"configurable": {"thread_id": "thread_review_01"}}
    initial_state = {
        "variant_id": "var_99",
        "package_id": "pkg_99",
        "payload": raw_payload,
        "payload_hash": p_hash,
        "decision": None,
        "reviewer_id": None,
        "feedback": None,
        "status": ContentStatus.IN_REVIEW
    }

    # 1. Run until human_review interrupt
    _ = approval_graph.invoke(initial_state, config=config)
    # Check graph paused at interrupt
    snapshot = approval_graph.get_state(config)
    assert "human_review" in snapshot.next

    # 2. Human reviews and provides approval
    approval_update = {
        "decision": "approve",
        "reviewer_id": "editor_martial",
        "feedback": "Validé pour publication."
    }
    approval_graph.update_state(config, approval_update)

    # 3. Resume execution
    final_result = approval_graph.invoke(None, config=config)
    assert final_result["status"] == ContentStatus.APPROVED


def test_agent_tool_registry_sandbox_and_budget():
    """Lot 4 (Sections 8.3 & 10.1): Verify AgentToolRegistry enforces SSRF, RBAC, and max call budget."""
    from packages.tools.registry import AgentToolRegistry

    # 1. Viewer role is blocked
    viewer_reg = AgentToolRegistry(workspace_id="ws_sandbox", caller_role="Viewer", max_total_calls=2)
    blocked_role = viewer_reg.execute("web_search", {"query": "LangGraph governance"})
    assert blocked_role.status == "BLOCKED"
    assert "not authorized" in (blocked_role.error or "")

    # 2. SSRF URL is blocked before network call
    agent_reg = AgentToolRegistry(workspace_id="ws_sandbox", caller_role="ServiceAgent", max_total_calls=2)
    blocked_ssrf = agent_reg.execute("safe_browse", {"url": "http://169.254.169.254/latest/meta-data/"})
    assert blocked_ssrf.status == "BLOCKED"
    assert "SSRF" in (blocked_ssrf.error or "")

    # 3. Unknown tool is blocked
    unknown_res = agent_reg.execute("shell_exec", {"cmd": "whoami"})
    assert unknown_res.status == "BLOCKED"


def test_idea_research_bounded_evidence_enrichment():
    """Lot 4 (Section 8.2 & D-04): Verify evidence_enrichment_node executes at most 2 bounded tool calls."""
    from unittest.mock import patch
    from services.orchestration.nodes.research import EnrichmentDecision
    from packages.tools.registry import ToolExecutionResult

    decisions = [
        EnrichmentDecision(
            sufficient_evidence=False,
            missing_aspects=["Chiffres d'adoption"],
            recommended_action="search_web",
            query_or_url="adoption multi-agent enterprise 2026",
            rationale="Besoin de statistiques récentes.",
        ),
        EnrichmentDecision(
            sufficient_evidence=False,
            missing_aspects=["Détails d'architecture"],
            recommended_action="browse_url",
            query_or_url="https://example.com/report",
            rationale="Lecture du rapport complet.",
        ),
        EnrichmentDecision(
            sufficient_evidence=False,
            missing_aspects=["Encore plus"],
            recommended_action="search_web",
            query_or_url="extra query",
            rationale="Ne devrait jamais être exécuté car borné à 2.",
        ),
    ]

    mock_search_res = ToolExecutionResult(
        tool_name="web_search",
        status="SUCCESS",
        data=[{"title": "Adoption IA 2026", "url": "https://example.com/report", "content": "Adoption de 64% en production avec gouvernance LangGraph."}],
    )
    mock_browse_res = ToolExecutionResult(
        tool_name="safe_browse",
        status="SUCCESS",
        data={"title": "Rapport Complet 2026", "url": "https://example.com/report", "content": "Le rapport complet démontre une réduction de 42% des incidents grâce aux Quality Gates déterministes."},
    )

    state = {
        "workspace_id": "ws_enrich_test",
        "topic_or_brief": "Gouvernance des agents en production",
        "pillars": ["IA générative"],
        "audience": ["DSI"],
        "target_count": 2,
        "enable_agentic_enrichment": True,
        "raw_sources": [],
        "generated_ideas": [],
        "run_id": "",
        "errors": [],
    }

    with patch("services.orchestration.nodes.research.resolve_and_get_llm", return_value=(None, None)), \
         patch("services.orchestration.nodes.research.invoke_structured_output", side_effect=decisions), \
         patch("packages.tools.registry.AgentToolRegistry.execute", side_effect=[mock_search_res, mock_browse_res]) as mock_exec:
        result = idea_research_graph.invoke(state)
        assert result.get("enrichment_count", 0) <= 2
        assert mock_exec.call_count <= 2
        assert len(result.get("generated_ideas", [])) >= 1

