from services.orchestration.graphs.idea_research import graph as idea_research_graph
from services.orchestration.graphs.content_production import graph as content_production_graph
from services.orchestration.graphs.approval import graph as approval_graph
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash


def test_idea_research_graph_execution():
    state = {
        "workspace_id": "ws_test",
        "topic_or_brief": "Systèmes multi-agents gouvernés",
        "pillars": ["IA générative", "Orchestration"],
        "audience": ["Tech Leads"],
        "target_count": 10,
        "raw_sources": [],
        "generated_ideas": [],
        "run_id": "",
        "errors": []
    }
    result = idea_research_graph.invoke(state)
    ideas = result.get("generated_ideas", [])
    assert len(ideas) >= 10
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
        "sources": [{"canonical_url": "https://example.com/source", "facts": []}],
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
