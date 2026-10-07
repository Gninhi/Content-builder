from datetime import datetime, timedelta, timezone
from infra.db.database import SessionLocal, init_db
from infra.db.repository import ContentOpsRepository
from services.publisher.worker import PublisherWorker
from services.orchestration.graphs.idea_research import graph as idea_research_graph
from services.orchestration.graphs.content_production import graph as content_production_graph
from services.orchestration.graphs.strategy_insights import graph as strategy_insights_graph
from packages.domain.state_machine import ContentStatus


def test_complete_contentops_pipeline_e2e():
    init_db()
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)

        # 1. Create Workspace
        ws = repo.create_workspace(name="E2E Test Workspace", timezone="UTC", owner_id="martial_gninhi")
        assert ws.id is not None

        # 2. Create Brand Profile
        bp = repo.create_or_version_brand_profile(
            workspace_id=ws.id,
            audience=["CTOs", "Lead Engineers"],
            voice="Direct, pragmatique et expert",
            pillars=["Systèmes multi-agents", "Gouvernance IA"],
            prohibited_topics=["Crypto", "Dénigrement"],
            cta_policy={"allowed_ctas": ["Partagez votre retour d'expérience"]}
        )
        assert bp.version == 1

        # 3. Ingest Content Source
        source = repo.add_source(
            workspace_id=ws.id,
            source_type="url",
            canonical_url="https://arxiv.org/abs/2601.99999",
            raw_content_ref="storage/sources/e2e_source.txt",
            extracted_facts=[{"fact_id": "fact_e2e_1", "claim": "Les systèmes déterministes évitent les boucles infinies de publication.", "confidence": 0.99}],
            provenance={"author": "AI Research Group", "verified": True}
        )
        assert source.id is not None

        # 4. Ideation via LangGraph
        research_state = {
            "workspace_id": ws.id,
            "topic_or_brief": "Gouvernance éditoriale des agents",
            "pillars": bp.pillars,
            "audience": bp.audience,
            "target_count": 10,
            "raw_sources": [{"url": source.canonical_url, "content": "Benchmark gouvernance"}],
            "generated_ideas": [],
            "run_id": "",
            "errors": []
        }
        res_ideas = idea_research_graph.invoke(research_state)
        ideas = res_ideas.get("generated_ideas", [])
        assert len(ideas) >= 10

        selected_idea = ideas[0]
        idea_model = repo.save_idea(
            workspace_id=ws.id,
            title=selected_idea["title"],
            angle=selected_idea["angle"],
            pillar="Gouvernance IA",
            audience=selected_idea["target_audience"],
            evidence_refs=selected_idea["evidence"],
            novelty_score=selected_idea["novelty_score"],
            relevance_score=selected_idea["relevance_score"],
            effort_score=selected_idea["effort_score"],
            priority=selected_idea["priority"],
            risks=selected_idea["risks"]
        )

        # 5. Create Brief
        brief = repo.create_brief(
            workspace_id=ws.id,
            idea_id=idea_model.id,
            objective="Démontrer l'absolue nécessité du contrôle déterministe pour publier sur LinkedIn",
            platform_targets=["linkedin", "x"]
        )
        assert brief.status == ContentStatus.BRIEFED.value

        # 6. Content Production & Quality Gate via LangGraph
        prod_state = {
            "workspace_id": ws.id,
            "brief_id": brief.id,
            "objective": brief.objective,
            "angle": selected_idea["angle"],
            "target_platforms": brief.platform_targets,
            "brand_voice": bp.voice,
            "prohibited_topics": bp.prohibited_topics,
            "cta_policy": bp.cta_policy,
            "sources": [{"canonical_url": source.canonical_url, "facts": source.extracted_facts}],
            "requirements": {},
            "generated_variants": [],
            "qa_results": {},
            "status": ContentStatus.DRAFT,
            "run_id": "run_e2e_prod",
            "errors": []
        }
        prod_res = content_production_graph.invoke(prod_state)
        assert prod_res["qa_results"]["overall_passed"] is True
        assert prod_res["status"] == ContentStatus.IN_REVIEW

        package = repo.create_content_package(
            brief_id=brief.id,
            version=1,
            qa_score=prod_res["qa_results"]["overall_score"]
        )

        variants = []
        for v in prod_res["generated_variants"]:
            vm = repo.add_variant(
                package_id=package.id,
                platform=v["platform"],
                hook=v["hook"],
                body=v["body"],
                cta=v["cta"],
                hashtags=v["hashtags"],
                media_spec=v["media_spec"],
                claims=v["claims"]
            )
            vm.status = ContentStatus.IN_REVIEW.value
            db.commit()
            variants.append(vm)

        linkedin_variant = [v for v in variants if v.platform == "linkedin"][0]

        # 7. Human Review & Approval (HITL)
        approval = repo.record_approval(
            variant_id=linkedin_variant.id,
            decision="approve",
            reviewer_id="martial_owner",
            feedback="Excellente publication, validée."
        )
        assert approval.decision == "approve"
        assert approval.payload_hash == linkedin_variant.payload_hash
        assert linkedin_variant.status == ContentStatus.APPROVED.value

        # 8. Scheduling with Idempotency Key
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=2)
        job = repo.schedule_publication(
            workspace_id=ws.id,
            variant_id=linkedin_variant.id,
            scheduled_at=scheduled_time
        )
        assert job.status == ContentStatus.SCHEDULED.value
        assert len(job.idempotency_key) == 64

        # 9. Publisher Worker Execution (Simulated Dispatcher)
        worker = PublisherWorker(db)
        pub_result = worker.execute_job(job.id)
        assert pub_result["status"] == "SUCCESS"
        assert pub_result["receipt"]["platform"] == "linkedin"
        assert linkedin_variant.status == ContentStatus.PUBLISHED.value

        # 10. Record Metric Snapshot
        metric = repo.record_metric_snapshot(
            post_id=pub_result["post_id"],
            impressions=2400,
            engagements=180,
            clicks=45,
            comments=18,
            shares=12
        )
        assert metric.impressions == 2400

        # 11. Generate Strategy Insights
        insights_res = strategy_insights_graph.invoke({
            "workspace_id": ws.id,
            "pillars": bp.pillars,
            "metric_snapshots": [{"impressions": 2400, "engagements": 180}],
            "hypotheses": [],
            "recommendations": [],
            "confidence_levels": {},
            "status": "PENDING"
        })
        assert len(insights_res["hypotheses"]) > 0
        assert insights_res["hypotheses"][0]["confidence_level"] > 0.5
        assert insights_res["status"] == "COMPLETED"

    finally:
        db.close()
