from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import re

from infra.db.models import (
    WorkspaceModel,
    BrandProfileModel,
    ContentSourceModel,
    VeilleSourceModel,
    SignalModel,
    IdeaModel,
    ContentBriefModel,
    ContentPackageModel,
    ContentVariantModel,
    ApprovalModel,
    PublicationJobModel,
    PublishedPostModel,
    MetricSnapshotModel,
    AgentRunModel,
    ConnectedSocialAccountModel,
    WorkspaceLLMSettingsModel,
    UserModel,
    WorkspaceMemberModel,
    UserSessionModel,
    UserRefreshTokenModel,
    WorkspaceInvitationModel,
    AuditLogModel,
    utc_now,
)
from packages.domain.state_machine import ContentStatus, ContentStateMachine
from packages.domain.idempotency import compute_payload_hash, compute_idempotency_key


class ContentOpsRepository:
    def __init__(self, db: Session):
        self.db = db

    # ----------------- Workspaces -----------------
    def create_workspace(self, name: str, timezone: str = "UTC", owner_id: str = "owner_1") -> WorkspaceModel:
        ws = WorkspaceModel(
            id=f"ws_{uuid.uuid4().hex[:12]}",
            name=name,
            timezone=timezone,
            owner_id=owner_id
        )
        self.db.add(ws)
        self.db.commit()
        self.db.refresh(ws)
        return ws

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceModel]:
        ws = self.db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
        if ws:
            return ws
        for obj in self.db.new:
            if isinstance(obj, WorkspaceModel) and getattr(obj, "id", None) == workspace_id:
                return obj
        return None

    def ensure_workspace(self, workspace_id: str, name: Optional[str] = None, owner_id: str = "system") -> WorkspaceModel:
        """Finds or creates a workspace to maintain referential integrity across test and production environments."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            # Check if workspace was added to the pending session objects in the same transaction
            for obj in self.db.new:
                if isinstance(obj, WorkspaceModel) and getattr(obj, "id", None) == workspace_id:
                    return obj
            ws = WorkspaceModel(
                id=workspace_id,
                name=name or f"Workspace {workspace_id}",
                timezone="UTC",
                owner_id=owner_id
            )
            self.db.add(ws)
            self.db.commit()
            self.db.refresh(ws)
        return ws


    def get_workspace_llm_settings(self, workspace_id: str) -> Optional[WorkspaceLLMSettingsModel]:
        return self.db.query(WorkspaceLLMSettingsModel).filter(WorkspaceLLMSettingsModel.workspace_id == workspace_id).first()

    def upsert_workspace_llm_settings(
        self,
        workspace_id: str,
        default_provider_id: str,
        default_model_id: str,
        default_temperature: float = 0.7,
        task_overrides: Optional[Dict[str, Any]] = None,
        provider_settings: Optional[Dict[str, Any]] = None,
    ) -> WorkspaceLLMSettingsModel:
        self.ensure_workspace(workspace_id)
        settings = self.get_workspace_llm_settings(workspace_id)
        if not settings:
            settings = WorkspaceLLMSettingsModel(
                id=f"llm_cfg_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace_id,
                default_provider_id=default_provider_id,
                default_model_id=default_model_id,
                default_temperature=default_temperature,
                task_overrides=task_overrides or {},
                provider_settings=provider_settings or {},
            )
            self.db.add(settings)
        else:
            setattr(settings, "default_provider_id", default_provider_id)
            setattr(settings, "default_model_id", default_model_id)
            setattr(settings, "default_temperature", default_temperature)
            if task_overrides is not None:
                setattr(settings, "task_overrides", task_overrides)
            if provider_settings is not None:
                setattr(settings, "provider_settings", provider_settings)

        self.db.commit()
        self.db.refresh(settings)
        return settings

    # ----------------- Brand Profiles -----------------
    def create_or_version_brand_profile(
        self,
        workspace_id: str,
        audience: List[str],
        voice: str,
        pillars: List[str],
        prohibited_topics: List[str],
        cta_policy: Dict[str, Any]
    ) -> BrandProfileModel:
        latest = (
            self.db.query(BrandProfileModel)
            .filter(BrandProfileModel.workspace_id == workspace_id)
            .order_by(BrandProfileModel.version.desc())
            .first()
        )
        next_version = (latest.version + 1) if latest else 1
        bp = BrandProfileModel(
            id=f"bp_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            version=next_version,
            audience=audience,
            voice=voice,
            pillars=pillars,
            prohibited_topics=prohibited_topics,
            cta_policy=cta_policy
        )
        self.db.add(bp)
        self.db.commit()
        self.db.refresh(bp)
        return bp

    def get_latest_brand_profile(self, workspace_id: str) -> Optional[BrandProfileModel]:
        return (
            self.db.query(BrandProfileModel)
            .filter(BrandProfileModel.workspace_id == workspace_id)
            .order_by(BrandProfileModel.version.desc())
            .first()
        )

    # ----------------- Content Sources -----------------
    def add_source(
        self,
        workspace_id: str,
        source_type: str,
        raw_content_ref: str,
        extracted_facts: List[Dict[str, Any]],
        provenance: Dict[str, Any],
        canonical_url: Optional[str] = None
    ) -> ContentSourceModel:
        # Deduplication check via canonical_url or content hash
        if canonical_url:
            existing = (
                self.db.query(ContentSourceModel)
                .filter(
                    ContentSourceModel.workspace_id == workspace_id,
                    ContentSourceModel.canonical_url == canonical_url
                )
                .first()
            )
            if existing:
                return existing

        source = ContentSourceModel(
            id=f"src_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            type=source_type,
            canonical_url=canonical_url,
            raw_content_ref=raw_content_ref,
            extracted_facts=extracted_facts,
            provenance=provenance,
            status="ingested"
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def list_sources(self, workspace_id: str) -> List[ContentSourceModel]:
        return self.db.query(ContentSourceModel).filter(ContentSourceModel.workspace_id == workspace_id).all()

    # ----------------- Veille Sources -----------------
    def create_veille_source(
        self,
        workspace_id: str,
        name: str,
        url: str,
        axis: str,
        trust_level: str = "B",
        source_type: str = "web"
    ) -> VeilleSourceModel:
        self.ensure_workspace(workspace_id)
        source = VeilleSourceModel(
            id=f"vsrc_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            name=name,
            url=url,
            axis=axis.lower(),
            trust_level=trust_level.upper(),
            source_type=source_type.lower(),
            is_active=True,
            health_status="HEALTHY",
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_veille_source(self, source_id: str, workspace_id: Optional[str] = None) -> Optional[VeilleSourceModel]:
        q = self.db.query(VeilleSourceModel).filter(VeilleSourceModel.id == source_id)
        if workspace_id:
            q = q.filter(VeilleSourceModel.workspace_id == workspace_id)
        return q.first()

    def update_veille_source(
        self,
        source_id: str,
        workspace_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        axis: Optional[str] = None,
        trust_level: Optional[str] = None,
        source_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        health_status: Optional[str] = None,
        error_message: Optional[str] = None,
        last_polled_at: Optional[datetime] = None,
    ) -> Optional[VeilleSourceModel]:
        source = self.get_veille_source(source_id, workspace_id)
        if not source:
            return None
        if name is not None:
            source.name = name
        if url is not None:
            source.url = url
        if axis is not None:
            source.axis = axis.lower()
        if trust_level is not None:
            source.trust_level = trust_level.upper()
        if source_type is not None:
            source.source_type = source_type.lower()
        if is_active is not None:
            source.is_active = is_active
        if health_status is not None:
            source.health_status = health_status
        if error_message is not None:
            source.error_message = error_message
        if last_polled_at is not None:
            source.last_polled_at = last_polled_at
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete_veille_source(self, source_id: str, workspace_id: str) -> bool:
        source = self.get_veille_source(source_id, workspace_id)
        if not source:
            return False
        self.db.delete(source)
        self.db.commit()
        return True

    def list_veille_sources(
        self,
        workspace_id: str,
        axis: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[VeilleSourceModel]:
        q = self.db.query(VeilleSourceModel).filter(VeilleSourceModel.workspace_id == workspace_id)
        if axis:
            q = q.filter(VeilleSourceModel.axis == axis.lower())
        if is_active is not None:
            q = q.filter(VeilleSourceModel.is_active == is_active)
        return q.order_by(VeilleSourceModel.created_at.desc()).all()

    def seed_default_veille_sources(self, workspace_id: str) -> List[VeilleSourceModel]:
        existing = self.list_veille_sources(workspace_id)
        if existing:
            return existing

        default_sources = [
            # Axe IA
            ("ArXiv cs.AI / cs.CL", "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL", "ia", "A", "arxiv"),
            ("Hugging Face Daily Papers", "https://huggingface.co/papers", "ia", "A", "web"),
            ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "ia", "B", "rss"),
            ("OpenAI Research & Updates", "https://openai.com/news/rss.xml", "ia", "A", "rss"),
            ("CNIL Veille & IA France", "https://www.cnil.fr/fr/rss.xml", "ia", "A", "rss"),

            # Axe Frameworks & Outils
            ("LangChain & LangGraph Releases", "https://api.github.com/repos/langchain-ai/langgraph/releases", "frameworks", "A", "github"),
            ("FastAPI Releases", "https://api.github.com/repos/tiangolo/fastapi/releases", "frameworks", "A", "github"),
            ("vLLM Releases", "https://api.github.com/repos/vllm-project/vllm/releases", "frameworks", "A", "github"),
            ("Hacker News AI & Tools", "https://hn.algolia.com/api/v1/search_by_date?tags=story&query=AI+tools", "frameworks", "B", "hackernews"),

            # Axe Évolution des Métiers (France & Europe)
            ("Les Echos - Tech & Économie", "https://www.lesechos.fr/rss/tech-medias.xml", "metiers", "A", "rss"),
            ("L'Usine Digitale - Emploi & IA", "https://www.usine-digitale.fr/rss/transformation-numerique/", "metiers", "A", "rss"),
            ("DARES & France Travail Études", "https://dares.travail-emploi.gouv.fr/rss", "metiers", "A", "rss"),
            ("EU AI Act & Future of Work Hub", "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai", "metiers", "A", "web"),
        ]

        created = []
        for name, url, axis, trust, stype in default_sources:
            src = self.create_veille_source(
                workspace_id=workspace_id,
                name=name,
                url=url,
                axis=axis,
                trust_level=trust,
                source_type=stype
            )
            created.append(src)
        return created

    # ----------------- Signals (Veille Grounding) -----------------
    def save_signal(
        self,
        workspace_id: str,
        title: str,
        summary: str,
        axis: str,
        trust_level: str,
        qualification_score: float,
        qualification_criteria: Dict[str, Any],
        facts: List[Dict[str, Any]],
        executive_takeaway: str,
        canonical_url: Optional[str] = None,
        source_id: Optional[str] = None,
        raw_content_ref: Optional[str] = None,
        status: str = "QUALIFIED",
        is_synthetic: bool = False,
        max_dedup_days: int = 90
    ) -> SignalModel:
        self.ensure_workspace(workspace_id)
        clean_url = canonical_url.strip().lower() if canonical_url else ""
        url_hash = hashlib.sha256(clean_url.encode()).hexdigest() if clean_url else hashlib.sha256(title.strip().lower().encode()).hexdigest()
        clean_title = re.sub(r"[^a-z0-9]", "", title.lower())
        title_hash = hashlib.sha256(clean_title.encode()).hexdigest()

        cutoff = utc_now() - timedelta(days=max_dedup_days)
        existing = (
            self.db.query(SignalModel)
            .filter(
                SignalModel.workspace_id == workspace_id,
                (SignalModel.url_hash == url_hash) | (SignalModel.title_hash == title_hash),
                SignalModel.created_at >= cutoff
            )
            .first()
        )
        if existing:
            if qualification_score > existing.qualification_score:
                existing.qualification_score = round(qualification_score, 2)
                existing.qualification_criteria = qualification_criteria
                if facts:
                    existing.facts = facts
                self.db.commit()
                self.db.refresh(existing)
            return existing

        signal = SignalModel(
            id=f"sig_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            source_id=source_id,
            canonical_url=canonical_url,
            url_hash=url_hash,
            title=title.strip(),
            title_hash=title_hash,
            summary=summary.strip(),
            axis=axis.lower(),
            trust_level=trust_level.upper(),
            qualification_score=round(qualification_score, 2),
            qualification_criteria=qualification_criteria,
            facts=facts,
            executive_takeaway=executive_takeaway.strip(),
            raw_content_ref=raw_content_ref,
            status=status,
            is_synthetic=is_synthetic,
            created_at=utc_now()
        )
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal

    def get_signal(self, signal_id: str, workspace_id: Optional[str] = None) -> Optional[SignalModel]:
        q = self.db.query(SignalModel).filter(SignalModel.id == signal_id)
        if workspace_id:
            q = q.filter(SignalModel.workspace_id == workspace_id)
        return q.first()

    def list_signals(
        self,
        workspace_id: str,
        axis: Optional[str] = None,
        trust_level: Optional[str] = None,
        min_score: Optional[float] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[SignalModel]:
        q = self.db.query(SignalModel).filter(SignalModel.workspace_id == workspace_id)
        if axis:
            q = q.filter(SignalModel.axis == axis.lower())
        if trust_level:
            q = q.filter(SignalModel.trust_level == trust_level.upper())
        if min_score is not None:
            q = q.filter(SignalModel.qualification_score >= min_score)
        if status:
            q = q.filter(SignalModel.status == status)
        return q.order_by(SignalModel.created_at.desc()).limit(limit).all()

    def update_signal_status(self, signal_id: str, workspace_id: str, status: str) -> Optional[SignalModel]:
        sig = self.get_signal(signal_id, workspace_id)
        if not sig:
            return None
        sig.status = status
        self.db.commit()
        self.db.refresh(sig)
        return sig

    def count_signals(self, workspace_id: str, axis: Optional[str] = None) -> int:
        q = self.db.query(SignalModel).filter(SignalModel.workspace_id == workspace_id)
        if axis:
            q = q.filter(SignalModel.axis == axis.lower())
        return q.count()

    # ----------------- Ideas -----------------
    def save_idea(
        self,
        workspace_id: str,
        title: str,
        angle: str,
        pillar: str,
        audience: str,
        evidence_refs: List[Dict[str, Any]],
        novelty_score: float,
        relevance_score: float,
        effort_score: float,
        priority: str,
        risks: List[str],
        signal_id: Optional[str] = None
    ) -> IdeaModel:
        self.ensure_workspace(workspace_id)
        # Check uniqueness by title in workspace to prevent duplicate cards
        clean_title = title.strip()
        existing = (
            self.db.query(IdeaModel)
            .filter(
                IdeaModel.workspace_id == workspace_id,
                IdeaModel.title == clean_title
            )
            .first()
        )
        if existing:
            if signal_id and not existing.signal_id:
                existing.signal_id = signal_id
                self.db.commit()
                self.db.refresh(existing)
            return existing

        total = round((novelty_score * 0.35) + (relevance_score * 0.45) - (effort_score * 0.20), 2)
        idea = IdeaModel(
            id=f"idea_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            signal_id=signal_id,
            title=clean_title,
            angle=angle,
            pillar=pillar,
            audience=audience,
            evidence_refs=evidence_refs,
            novelty_score=novelty_score,
            relevance_score=relevance_score,
            effort_score=effort_score,
            total_score=total,
            priority=priority,
            risks=risks,
            status=ContentStatus.IDEA.value
        )
        self.db.add(idea)
        self.db.commit()
        self.db.refresh(idea)
        return idea

    def list_ideas(self, workspace_id: str, status: Optional[str] = None) -> List[IdeaModel]:
        q = self.db.query(IdeaModel).filter(IdeaModel.workspace_id == workspace_id)
        if status:
            q = q.filter(IdeaModel.status == status)
        return q.order_by(IdeaModel.total_score.desc()).all()

    def get_idea_by_signal_id(self, signal_id: str, workspace_id: str) -> Optional[IdeaModel]:
        """Finds an existing idea created from a specific monitoring signal for idempotency."""
        return (
            self.db.query(IdeaModel)
            .filter(
                IdeaModel.workspace_id == workspace_id,
                IdeaModel.signal_id == signal_id
            )
            .first()
        )

    def convert_signal_to_idea(
        self,
        signal_id: str,
        workspace_id: str,
    ) -> IdeaModel:
        """
        Transactionally converts an approved monitoring signal into a verified editorial idea.
        Ensures signal exists, is eligible, preserves source facts as evidence, and maintains idempotency.
        """
        signal = self.get_signal(signal_id=signal_id, workspace_id=workspace_id)
        if not signal:
            raise ValueError("Signal introuvable dans ce workspace.")
        if signal.status == "REJECTED":
            raise ValueError("Impossible de convertir un signal rejeté.")

        # Idempotency / Double-click protection: return existing idea if already converted
        existing = self.get_idea_by_signal_id(signal_id=signal_id, workspace_id=workspace_id)
        if existing:
            if signal.status != "CONVERTED":
                signal.status = "CONVERTED"
                self.db.commit()
            return existing

        # Map axis to editorial pillar
        axis_pillars = {
            "ia": "IA générative & LLMs",
            "frameworks": "Frameworks & Outils",
            "metiers": "Évolution des Métiers",
        }
        pillar = axis_pillars.get(str(signal.axis).lower(), "Stratégie IA & Automatisation")

        # Map audience from brand profile if available
        brand = self.get_latest_brand_profile(workspace_id)
        audience = brand.audience[0] if (brand and brand.audience) else "Tech Leads & DSI"

        # Format evidence refs directly grounded on verified signal facts
        facts = list(signal.facts) if signal.facts else []
        evidence_refs: List[Dict[str, Any]] = []
        source_ref = signal.canonical_url or f"signal://{signal.id}"
        for f in facts:
            if isinstance(f, dict):
                claim_text = f.get("fact") or f.get("claim") or ""
                src_url = f.get("source_url") or source_ref
                quote_text = f.get("quote") or claim_text
                evidence_refs.append({
                    "claim": claim_text,
                    "source_id": src_url,
                    "quote": quote_text,
                    "verified": True,
                })
        if not evidence_refs:
            evidence_refs.append({
                "claim": signal.summary,
                "source_id": source_ref,
                "quote": signal.executive_takeaway or signal.summary,
                "verified": True,
            })

        # Scaled scores from signal qualification (0.0 - 5.0 scaled to 0 - 100)
        scaled_score = min(100.0, max(0.0, round((float(signal.qualification_score) / 5.0) * 100.0, 1)))
        novelty = scaled_score
        relevance = min(100.0, max(0.0, scaled_score + 5.0))
        effort = 35.0  # Execution effort standard

        priority = "high" if str(signal.trust_level).upper() == "A" else "medium"

        idea = self.save_idea(
            workspace_id=workspace_id,
            title=signal.title,
            angle=signal.executive_takeaway or signal.summary,
            pillar=pillar,
            audience=audience,
            evidence_refs=evidence_refs,
            novelty_score=novelty,
            relevance_score=relevance,
            effort_score=effort,
            priority=priority,
            risks=["À valider avec le profil de marque avant production"],
            signal_id=signal.id,
        )

        signal.status = "CONVERTED"
        self.db.commit()
        self.db.refresh(idea)
        return idea

    # ----------------- Briefs & Packages -----------------
    def create_brief(
        self,
        workspace_id: str,
        objective: str,
        idea_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        platform_targets: Optional[List[str]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> ContentBriefModel:
        if idea_id:
            idea = self.db.query(IdeaModel).filter(IdeaModel.id == idea_id).first()
            if idea:
                setattr(idea, "status", ContentStatus.BRIEFED.value)

        brief = ContentBriefModel(
            id=f"brief_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            idea_id=idea_id,
            objective=objective,
            campaign_id=campaign_id,
            platform_targets=platform_targets or ["linkedin", "x"],
            requirements=requirements or {},
            status=ContentStatus.BRIEFED.value
        )
        self.db.add(brief)
        self.db.commit()
        self.db.refresh(brief)
        return brief

    def create_content_package(
        self,
        brief_id: str,
        version: int = 1,
        model_metadata: Optional[Dict[str, Any]] = None,
        qa_score: float = 0.0
    ) -> ContentPackageModel:
        package = ContentPackageModel(
            id=f"pkg_{uuid.uuid4().hex[:12]}",
            brief_id=brief_id,
            version=version,
            model_metadata=model_metadata or {},
            qa_score=qa_score,
            status=ContentStatus.DRAFT.value
        )
        self.db.add(package)
        self.db.commit()
        self.db.refresh(package)
        return package

    def add_variant(
        self,
        package_id: str,
        platform: str,
        hook: str,
        body: str,
        cta: str,
        hashtags: Optional[List[str]] = None,
        media_spec: Optional[Dict[str, Any]] = None,
        claims: Optional[List[Dict[str, Any]]] = None,
        degraded: bool = False
    ) -> ContentVariantModel:
        m_spec = dict(media_spec or {})
        if degraded:
            m_spec["degraded"] = True

        raw_payload = {
            "platform": platform,
            "hook": hook,
            "body": body,
            "cta": cta,
            "hashtags": hashtags or [],
            "media_spec": m_spec,
        }
        p_hash = compute_payload_hash(raw_payload)

        variant = ContentVariantModel(
            id=f"var_{uuid.uuid4().hex[:12]}",
            package_id=package_id,
            platform=platform,
            hook=hook,
            body=body,
            cta=cta,
            hashtags=hashtags or [],
            media_spec=m_spec,
            claims=claims or [],
            payload_hash=p_hash,
            degraded=degraded,
            status=ContentStatus.DRAFT.value
        )
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def record_approval(
        self,
        variant_id: str,
        decision: str,
        reviewer_id: str,
        workspace_id: Optional[str] = None,
        feedback: Optional[str] = None,
        edited_payload: Optional[Dict[str, Any]] = None
    ) -> ApprovalModel:
        query = self.db.query(ContentVariantModel)
        if workspace_id:
            query = (
                query.join(ContentPackageModel)
                .join(ContentBriefModel)
                .filter(ContentBriefModel.workspace_id == workspace_id)
            )
        variant = query.filter(ContentVariantModel.id == variant_id).first()
        if not variant:
            raise ValueError(f"Content variant '{variant_id}' not found or access denied for workspace.")

        current_status = ContentStatus(variant.status)

        if decision == "edit" and edited_payload:
            variant.hook = edited_payload.get("hook", variant.hook)
            variant.body = edited_payload.get("body", variant.body)
            variant.cta = edited_payload.get("cta", variant.cta)
            variant.hashtags = edited_payload.get("hashtags", variant.hashtags)
            variant.media_spec = edited_payload.get("media_spec", variant.media_spec)
            # Recompute payload hash
            raw = {
                "platform": variant.platform,
                "hook": variant.hook,
                "body": variant.body,
                "cta": variant.cta,
                "hashtags": variant.hashtags,
                "media_spec": variant.media_spec
            }
            setattr(variant, "payload_hash", compute_payload_hash(raw))
            # Edited draft goes to IN_REVIEW or APPROVED
            decision = "approve"

        # Apply state transition
        if decision == "approve":
            next_status = ContentStateMachine.transition(current_status, ContentStatus.APPROVED)
        elif decision == "reject":
            next_status = ContentStateMachine.transition(current_status, ContentStatus.REJECTED)
        elif decision in ("request_rewrite", "rewrite"):
            decision = "request_rewrite"
            next_status = ContentStateMachine.transition(current_status, ContentStatus.REWRITE_REQUESTED)
        else:
            raise ValueError(f"Unknown approval decision '{decision}'")

        setattr(variant, "status", next_status.value)

        approval = ApprovalModel(
            id=f"appr_{uuid.uuid4().hex[:12]}",
            variant_id=variant.id,
            decision=decision,
            reviewer_id=reviewer_id,
            feedback=feedback,
            payload_hash=variant.payload_hash,
            reviewed_at=datetime.now(timezone.utc)
        )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def schedule_publication(
        self,
        workspace_id: str,
        variant_id: str,
        scheduled_at: datetime
    ) -> PublicationJobModel:
        variant = (
            self.db.query(ContentVariantModel)
            .join(ContentPackageModel)
            .join(ContentBriefModel)
            .filter(
                ContentVariantModel.id == variant_id,
                ContentBriefModel.workspace_id == workspace_id
            )
            .first()
        )
        if not variant:
            raise ValueError(f"Variant '{variant_id}' not found or access denied for workspace '{workspace_id}'.")

        if variant.status not in (ContentStatus.APPROVED.value, ContentStatus.SCHEDULED.value):
            raise ValueError(f"Cannot schedule variant with status '{variant.status}'. Must be APPROVED.")

        # Normalize scheduled_at to timezone-aware UTC
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        else:
            scheduled_at = scheduled_at.astimezone(timezone.utc)

        # Verify an approval exists with the exact payload hash
        latest_approval = (
            self.db.query(ApprovalModel)
            .filter(
                ApprovalModel.variant_id == variant.id,
                ApprovalModel.decision == "approve",
                ApprovalModel.payload_hash == variant.payload_hash
            )
            .first()
        )
        if not latest_approval:
            raise ValueError("Integrity error: No valid approval found matching current payload hash.")

        idempotency_key = compute_idempotency_key(
            workspace_id=workspace_id,
            variant_id=str(variant.id),
            platform=str(variant.platform),
            scheduled_at=scheduled_at.isoformat(),
            version=1
        )

        # Check existing job (idempotent)
        existing_job = self.db.query(PublicationJobModel).filter(PublicationJobModel.idempotency_key == idempotency_key).first()
        if existing_job:
            return existing_job

        # Slot collision detection: check other jobs in same workspace and platform within 15 minutes
        collision_buffer = timedelta(minutes=15)
        existing_scheduled = (
            self.db.query(PublicationJobModel)
            .join(ContentVariantModel, PublicationJobModel.variant_id == ContentVariantModel.id)
            .join(ContentPackageModel, ContentVariantModel.package_id == ContentPackageModel.id)
            .join(ContentBriefModel, ContentPackageModel.brief_id == ContentBriefModel.id)
            .filter(
                ContentBriefModel.workspace_id == workspace_id,
                PublicationJobModel.platform == variant.platform,
                PublicationJobModel.status.in_([ContentStatus.SCHEDULED.value, ContentStatus.PUBLISHING.value])
            )
            .all()
        )
        for prev_job in existing_scheduled:
            if prev_job.idempotency_key == idempotency_key or prev_job.variant_id == variant.id:
                continue
            prev_dt = prev_job.scheduled_at
            if prev_dt.tzinfo is None:
                prev_dt = prev_dt.replace(tzinfo=timezone.utc)
            if abs((scheduled_at - prev_dt).total_seconds()) < collision_buffer.total_seconds():
                raise ValueError(
                    f"Publication slot collision: Another post is already scheduled for platform '{variant.platform}' at {prev_dt} (collision buffer: 15 minutes)."
                )

        setattr(variant, "status", ContentStatus.SCHEDULED.value)

        job = PublicationJobModel(
            id=f"job_{uuid.uuid4().hex[:12]}",
            variant_id=variant.id,
            platform=variant.platform,
            scheduled_at=scheduled_at,
            idempotency_key=idempotency_key,
            status=ContentStatus.SCHEDULED.value
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def record_published_post(
        self,
        job_id: str,
        external_post_id: str,
        final_payload: Dict[str, Any],
        platform: str,
        permalink: str
    ) -> PublishedPostModel:
        job = self.db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
        if job:
            setattr(job, "status", ContentStatus.PUBLISHED.value)
            if job.variant:
                setattr(job.variant, "status", ContentStatus.PUBLISHED.value)

        post = PublishedPostModel(
            id=f"post_{uuid.uuid4().hex[:12]}",
            job_id=job_id,
            external_post_id=external_post_id,
            final_payload=final_payload,
            platform=platform,
            published_at=datetime.now(timezone.utc),
            permalink=permalink
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    # ----------------- Metrics -----------------
    def record_metric_snapshot(
        self,
        post_id: str,
        impressions: int,
        engagements: int,
        clicks: int,
        comments: int,
        shares: int,
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> MetricSnapshotModel:
        metric = MetricSnapshotModel(
            id=f"met_{uuid.uuid4().hex[:12]}",
            post_id=post_id,
            observed_at=datetime.now(timezone.utc),
            impressions=impressions,
            engagements=engagements,
            clicks=clicks,
            comments=comments,
            shares=shares,
            raw_payload=raw_payload or {}
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    # ----------------- Agent Run Logging -----------------
    def log_agent_run(
        self,
        workspace_id: str,
        graph: str,
        node: str,
        trace_id: str,
        prompt_version: str,
        model: str,
        cost: float = 0.0,
        input_ref: Optional[str] = None,
        output_ref: Optional[str] = None,
        status: str = "completed"
    ) -> AgentRunModel:
        run = AgentRunModel(
            id=f"run_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            graph=graph,
            node=node,
            trace_id=trace_id,
            input_ref=input_ref,
            output_ref=output_ref,
            prompt_version=prompt_version,
            model=model,
            cost=cost,
            status=status
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    # ----------------- Workspace Isolated Queries -----------------
    def get_inbox_variants(self, workspace_id: str) -> List[ContentVariantModel]:
        return (
            self.db.query(ContentVariantModel)
            .join(ContentPackageModel)
            .join(ContentBriefModel)
            .filter(
                ContentBriefModel.workspace_id == workspace_id,
                ContentVariantModel.status == ContentStatus.IN_REVIEW.value
            )
            .all()
        )

    def get_editorial_calendar(self, workspace_id: str) -> Dict[str, Any]:
        scheduled_jobs = (
            self.db.query(PublicationJobModel)
            .options(joinedload(PublicationJobModel.variant))
            .join(ContentVariantModel)
            .join(ContentPackageModel)
            .join(ContentBriefModel)
            .filter(ContentBriefModel.workspace_id == workspace_id)
            .order_by(PublicationJobModel.scheduled_at.asc())
            .all()
        )
        published_posts = (
            self.db.query(PublishedPostModel)
            .join(PublicationJobModel)
            .join(ContentVariantModel)
            .join(ContentPackageModel)
            .join(ContentBriefModel)
            .filter(ContentBriefModel.workspace_id == workspace_id)
            .order_by(PublishedPostModel.published_at.desc())
            .all()
        )
        return {
            "scheduled": [
                {
                    "job_id": j.id,
                    "variant_id": j.variant_id,
                    "workspace_id": workspace_id,
                    "platform": j.platform,
                    "scheduled_at": j.scheduled_at,
                    "status": j.status,
                    "body_snippet": (j.variant.body[:80] + "...") if (j.variant and j.variant.body) else ""
                }
                for j in scheduled_jobs
            ],
            "published": [
                {
                    "post_id": p.id,
                    "job_id": p.job_id,
                    "workspace_id": workspace_id,
                    "platform": p.platform,
                    "published_at": p.published_at,
                    "external_post_id": p.external_post_id,
                    "url": p.permalink
                }
                for p in published_posts
            ]
        }

    # ----------------- Connected Social Accounts -----------------
    def store_connected_social_account(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        account_name: str,
        encrypted_blob: str,
        key_id: str = "v1",
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
        status: str = "ACTIVE"
    ) -> ConnectedSocialAccountModel:
        account = (
            self.db.query(ConnectedSocialAccountModel)
            .filter(
                ConnectedSocialAccountModel.workspace_id == workspace_id,
                ConnectedSocialAccountModel.provider == provider.lower(),
                ConnectedSocialAccountModel.account_id == account_id
            )
            .first()
        )
        if not account:
            account = ConnectedSocialAccountModel(
                id=f"csa_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace_id,
                provider=provider.lower(),
                account_id=account_id,
                account_name=account_name,
                encrypted_token_blob=encrypted_blob,
                key_id=key_id,
                scopes=scopes or [],
                expires_at=expires_at,
                status=status
            )
            self.db.add(account)
        else:
            setattr(account, "account_name", account_name)
            setattr(account, "encrypted_token_blob", encrypted_blob)
            setattr(account, "key_id", key_id)
            setattr(account, "scopes", scopes or [])
            setattr(account, "expires_at", expires_at)
            setattr(account, "status", status)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_connected_social_account(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> Optional[ConnectedSocialAccountModel]:
        return (
            self.db.query(ConnectedSocialAccountModel)
            .filter(
                ConnectedSocialAccountModel.workspace_id == workspace_id,
                ConnectedSocialAccountModel.provider == provider.lower(),
                ConnectedSocialAccountModel.account_id == account_id
            )
            .first()
        )

    def list_connected_social_accounts(
        self,
        workspace_id: str,
        provider: Optional[str] = None
    ) -> List[ConnectedSocialAccountModel]:
        q = self.db.query(ConnectedSocialAccountModel).filter(
            ConnectedSocialAccountModel.workspace_id == workspace_id
        )
        if provider:
            q = q.filter(ConnectedSocialAccountModel.provider == provider.lower())
        return q.all()

    def update_social_account_status(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        status: str
    ) -> bool:
        account = self.get_connected_social_account(workspace_id, provider, account_id)
        if not account:
            return False
        setattr(account, "status", status)
        self.db.commit()
        return True

    def delete_connected_social_account(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> bool:
        account = self.get_connected_social_account(workspace_id, provider, account_id)
        if not account:
            return False
        self.db.delete(account)
        self.db.commit()
        return True

    # ----------------- Users & Profiles -----------------
    def get_user(self, user_id: str) -> Optional[UserModel]:
        u = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if u:
            return u
        for obj in self.db.new:
            if isinstance(obj, UserModel) and getattr(obj, "id", None) == user_id:
                return obj
        return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.email == email.strip().lower()).first()

    def create_user(
        self,
        user_id: str,
        email: str,
        full_name: str = "",
        password_hash: Optional[str] = None,
        display_name: Optional[str] = None,
        job_title: Optional[str] = None,
        avatar_url: Optional[str] = None,
        timezone: str = "UTC",
        language: str = "fr",
        theme: str = "dark",
        notification_preferences: Optional[Dict[str, Any]] = None,
        ui_preferences: Optional[Dict[str, Any]] = None,
        email_verified: bool = False,
        cgu_version: Optional[str] = None,
        privacy_version: Optional[str] = None,
    ) -> UserModel:
        now = utc_now()
        user = UserModel(
            id=user_id,
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name,
            display_name=display_name,
            job_title=job_title,
            avatar_url=avatar_url,
            timezone=timezone,
            language=language,
            theme=theme,
            notification_preferences=notification_preferences or {},
            ui_preferences=ui_preferences or {},
            is_active=True,
            email_verified=email_verified,
            cgu_accepted_at=now if cgu_version else None,
            cgu_version=cgu_version,
            privacy_accepted_at=now if privacy_version else None,
            privacy_version=privacy_version,
            failed_login_attempts=0,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_or_create_user(
        self,
        user_id: str,
        default_role: str = "Viewer",
        workspace_id: Optional[str] = None
    ) -> UserModel:
        """Finds user or lazily provisions a default user account for backward compatibility."""
        user = self.get_user(user_id)
        if not user:
            user = self.create_user(
                user_id=user_id,
                email=f"{user_id}@contentops.internal",
                full_name=user_id.replace("_", " ").title(),
                display_name=user_id,
                job_title="Content Ops Contributor",
            )
            if workspace_id:
                self.add_workspace_member(workspace_id=workspace_id, user_id=user_id, role=default_role)
        return user

    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Optional[UserModel]:
        user = self.get_user(user_id)
        if not user:
            return None
        for key, value in updates.items():
            if hasattr(user, key) and key not in ("id", "password_hash", "is_active", "created_at"):
                setattr(user, key, value)
        setattr(user, "updated_at", utc_now())
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user_password(self, user_id: str, password_hash: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        setattr(user, "password_hash", password_hash)
        setattr(user, "updated_at", utc_now())
        self.db.commit()
        return True

    def anonymize_user(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        # Redact personal information
        anon_id = uuid.uuid4().hex[:8]
        setattr(user, "email", f"deleted_{anon_id}@anonymized.internal")
        setattr(user, "full_name", "Compte Supprimé")
        setattr(user, "display_name", None)
        setattr(user, "job_title", None)
        setattr(user, "avatar_url", None)
        setattr(user, "password_hash", None)
        setattr(user, "notification_preferences", {})
        setattr(user, "ui_preferences", {})
        setattr(user, "is_active", False)
        setattr(user, "updated_at", utc_now())
        # Revoke all sessions
        self.revoke_other_sessions(user_id=user_id, current_jti=None)
        self.db.commit()
        return True

    # ----------------- Workspaces & Memberships -----------------
    def get_workspace_member(self, workspace_id: str, user_id: str) -> Optional[WorkspaceMemberModel]:
        return (
            self.db.query(WorkspaceMemberModel)
            .filter(WorkspaceMemberModel.workspace_id == workspace_id, WorkspaceMemberModel.user_id == user_id)
            .first()
        )

    def add_workspace_member(self, workspace_id: str, user_id: str, role: str = "Viewer") -> WorkspaceMemberModel:
        self.ensure_workspace(workspace_id)
        self.get_or_create_user(user_id=user_id, default_role=role)
        existing = self.get_workspace_member(workspace_id, user_id)
        if existing:
            setattr(existing, "role", role)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        member = WorkspaceMemberModel(
            id=f"mem_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def get_user_memberships(self, user_id: str) -> List[WorkspaceMemberModel]:
        return self.db.query(WorkspaceMemberModel).filter(WorkspaceMemberModel.user_id == user_id).all()

    def get_user_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all workspaces the user belongs to, with computed roles."""
        memberships = self.get_user_memberships(user_id)
        membership_dict: Dict[str, str] = {str(m.workspace_id): str(m.role) for m in memberships}

        # Include workspaces where user is owner_id even if not explicitly in workspace_members
        owned_workspaces = self.db.query(WorkspaceModel).filter(WorkspaceModel.owner_id == user_id).all()
        for ow in owned_workspaces:
            ow_id = str(ow.id)
            if ow_id not in membership_dict:
                membership_dict[ow_id] = "Owner"

        if not membership_dict:
            return []

        workspaces = self.db.query(WorkspaceModel).filter(WorkspaceModel.id.in_(membership_dict.keys())).all()
        result = []
        for ws in workspaces:
            role = "Owner" if str(ws.owner_id) == user_id else membership_dict.get(str(ws.id), "Viewer")
            result.append({
                "workspace_id": str(ws.id),
                "name": str(ws.name),
                "role": role,
                "timezone": str(ws.timezone),
                "is_owner": (role.lower() == "owner" or str(ws.owner_id) == user_id),
            })
        return result

    def is_last_owner_of_any_workspace(self, user_id: str) -> Tuple[bool, List[str]]:
        """
        Checks whether the user is the sole active Owner of any workspace.
        Returns (is_last_owner, list_of_workspace_ids).
        """
        user_ws = self.get_user_workspaces(user_id)
        blocked_workspaces: List[str] = []

        for ws_info in user_ws:
            if not ws_info.get("is_owner"):
                continue
            ws_id = ws_info["workspace_id"]
            ws = self.get_workspace(ws_id)
            if not ws:
                continue

            # Count active owners for this workspace
            owner_user_ids = set()
            if ws.owner_id:
                owner_user = self.get_user(str(ws.owner_id))
                if owner_user and bool(owner_user.is_active):
                    owner_user_ids.add(str(ws.owner_id))

            other_owner_members = (
                self.db.query(WorkspaceMemberModel)
                .join(UserModel, WorkspaceMemberModel.user_id == UserModel.id)
                .filter(
                    WorkspaceMemberModel.workspace_id == ws_id,
                    WorkspaceMemberModel.role.ilike("owner"),
                    UserModel.is_active.is_(True),
                )
                .all()
            )
            for m in other_owner_members:
                owner_user_ids.add(str(m.user_id))

            # If user_id is the only owner in owner_user_ids
            if owner_user_ids == {user_id} or len(owner_user_ids) <= 1:
                blocked_workspaces.append(ws_id)

        return (len(blocked_workspaces) > 0, blocked_workspaces)

    # ----------------- User Sessions -----------------
    def create_session(
        self,
        user_id: str,
        token_jti: str,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> UserSessionModel:
        sess = UserSessionModel(
            id=f"sess_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            token_jti=token_jti,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(sess)
        self.db.commit()
        self.db.refresh(sess)
        return sess

    def get_session_by_jti(self, token_jti: str) -> Optional[UserSessionModel]:
        return self.db.query(UserSessionModel).filter(UserSessionModel.token_jti == token_jti).first()

    def list_user_sessions(self, user_id: str) -> List[UserSessionModel]:
        return (
            self.db.query(UserSessionModel)
            .filter(UserSessionModel.user_id == user_id)
            .order_by(UserSessionModel.last_active_at.desc())
            .all()
        )

    def touch_session(self, token_jti: str) -> None:
        sess = self.get_session_by_jti(token_jti)
        if sess and not sess.is_revoked:
            setattr(sess, "last_active_at", utc_now())
            self.db.commit()

    def revoke_session(self, user_id: str, session_id: str) -> bool:
        sess = (
            self.db.query(UserSessionModel)
            .filter(UserSessionModel.id == session_id, UserSessionModel.user_id == user_id)
            .first()
        )
        if not sess:
            return False
        setattr(sess, "is_revoked", True)
        self.db.commit()
        return True

    def revoke_other_sessions(self, user_id: str, current_jti: Optional[str] = None) -> int:
        q = self.db.query(UserSessionModel).filter(
            UserSessionModel.user_id == user_id,
            UserSessionModel.is_revoked.is_(False),
        )
        if current_jti:
            q = q.filter(UserSessionModel.token_jti != current_jti)
        sessions = q.all()
        for s in sessions:
            setattr(s, "is_revoked", True)
        self.db.commit()
        return len(sessions)

    # ----------------- Audit Logs -----------------
    def record_audit_log(
        self,
        user_id: str,
        event_type: str,
        severity: str = "INFO",
        workspace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLogModel:
        log = AuditLogModel(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_user_audit_logs(self, user_id: str, limit: int = 50) -> List[AuditLogModel]:
        return (
            self.db.query(AuditLogModel)
            .filter(AuditLogModel.user_id == user_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .all()
        )

    # ----------------- Refresh Tokens -----------------
    def create_refresh_token(
        self,
        user_id: str,
        token_hash: str,
        family_id: str,
        expires_at: datetime,
    ) -> UserRefreshTokenModel:
        rt = UserRefreshTokenModel(
            id=f"rt_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(rt)
        self.db.commit()
        self.db.refresh(rt)
        return rt

    def get_refresh_token_by_hash(self, token_hash: str) -> Optional[UserRefreshTokenModel]:
        return (
            self.db.query(UserRefreshTokenModel)
            .filter(UserRefreshTokenModel.token_hash == token_hash)
            .first()
        )

    def revoke_refresh_token(self, token_id: str) -> bool:
        rt = self.db.query(UserRefreshTokenModel).filter(UserRefreshTokenModel.id == token_id).first()
        if not rt:
            return False
        setattr(rt, "is_revoked", True)
        self.db.commit()
        return True

    def get_active_refresh_token_in_family(self, family_id: str) -> Optional[UserRefreshTokenModel]:
        """Returns the most recent non-revoked active refresh token in a family for rotation leeway."""
        return (
            self.db.query(UserRefreshTokenModel)
            .filter(
                UserRefreshTokenModel.family_id == family_id,
                UserRefreshTokenModel.is_revoked.is_(False),
                UserRefreshTokenModel.expires_at > utc_now(),
            )
            .order_by(UserRefreshTokenModel.created_at.desc())
            .first()
        )

    def revoke_refresh_token_family(self, family_id: str) -> int:
        """Revokes all refresh tokens in a family (e.g., token reuse detection)."""
        tokens = (
            self.db.query(UserRefreshTokenModel)
            .filter(
                UserRefreshTokenModel.family_id == family_id,
                UserRefreshTokenModel.is_revoked.is_(False),
            )
            .all()
        )
        for t in tokens:
            setattr(t, "is_revoked", True)
        self.db.commit()
        return len(tokens)

    def revoke_all_user_refresh_tokens(self, user_id: str) -> int:
        tokens = (
            self.db.query(UserRefreshTokenModel)
            .filter(
                UserRefreshTokenModel.user_id == user_id,
                UserRefreshTokenModel.is_revoked.is_(False),
            )
            .all()
        )
        for t in tokens:
            setattr(t, "is_revoked", True)
        self.db.commit()
        return len(tokens)

    def cleanup_expired_refresh_tokens(self) -> int:
        now = utc_now()
        deleted = (
            self.db.query(UserRefreshTokenModel)
            .filter(UserRefreshTokenModel.expires_at < now)
            .delete()
        )
        self.db.commit()
        return deleted

    # ----------------- Email Verification & Password Reset -----------------
    def set_email_verification_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        setattr(user, "email_verification_token_hash", token_hash)
        setattr(user, "email_verification_expires_at", expires_at)
        setattr(user, "updated_at", utc_now())
        self.db.commit()
        return True

    def get_user_by_verification_token_hash(self, token_hash: str) -> Optional[UserModel]:
        now = utc_now()
        return (
            self.db.query(UserModel)
            .filter(
                UserModel.email_verification_token_hash == token_hash,
                UserModel.email_verification_expires_at > now,
            )
            .first()
        )

    def verify_user_email(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        setattr(user, "email_verified", True)
        setattr(user, "email_verification_token_hash", None)
        setattr(user, "email_verification_expires_at", None)
        setattr(user, "updated_at", utc_now())
        self.db.commit()
        return True

    def set_password_reset_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        setattr(user, "password_reset_token_hash", token_hash)
        setattr(user, "password_reset_expires_at", expires_at)
        setattr(user, "updated_at", utc_now())
        self.db.commit()
        return True

    def get_user_by_password_reset_token_hash(self, token_hash: str) -> Optional[UserModel]:
        now = utc_now()
        return (
            self.db.query(UserModel)
            .filter(
                UserModel.password_reset_token_hash == token_hash,
                UserModel.password_reset_expires_at > now,
            )
            .first()
        )

    def reset_password_with_token(self, user_id: str, password_hash: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        setattr(user, "password_hash", password_hash)
        setattr(user, "password_reset_token_hash", None)
        setattr(user, "password_reset_expires_at", None)
        setattr(user, "failed_login_attempts", 0)
        setattr(user, "locked_until", None)
        setattr(user, "updated_at", utc_now())
        # Invalidate existing sessions and refresh tokens on password change
        self.revoke_other_sessions(user_id=user_id, current_jti=None)
        self.revoke_all_user_refresh_tokens(user_id=user_id)
        self.db.commit()
        return True

    def record_failed_login(
        self, user_id: str, max_attempts: int = 5, lock_duration_minutes: int = 15
    ) -> Tuple[int, Optional[datetime]]:
        user = self.get_user(user_id)
        if not user:
            return (0, None)
        attempts = int(user.failed_login_attempts or 0) + 1
        setattr(user, "failed_login_attempts", attempts)
        locked_until = None
        if attempts >= max_attempts:
            locked_until = utc_now() + timedelta(minutes=lock_duration_minutes)
            setattr(user, "locked_until", locked_until)
        setattr(user, "updated_at", utc_now())
        self.db.commit()
        return (attempts, locked_until)

    def reset_failed_logins(self, user_id: str) -> None:
        user = self.get_user(user_id)
        if user:
            setattr(user, "failed_login_attempts", 0)
            setattr(user, "locked_until", None)
            setattr(user, "updated_at", utc_now())
            self.db.commit()

    # ----------------- Workspace Invitations -----------------
    def create_invitation(
        self,
        workspace_id: str,
        email: str,
        role: str,
        invitation_code_hash: str,
        expires_at: datetime,
        created_by: str,
    ) -> WorkspaceInvitationModel:
        inv = WorkspaceInvitationModel(
            id=f"inv_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            email=email.strip().lower(),
            role=role,
            invitation_code_hash=invitation_code_hash,
            expires_at=expires_at,
            created_by=created_by,
        )
        self.db.add(inv)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def get_invitation_by_code_hash(self, code_hash: str) -> Optional[WorkspaceInvitationModel]:
        now = utc_now()
        return (
            self.db.query(WorkspaceInvitationModel)
            .filter(
                WorkspaceInvitationModel.invitation_code_hash == code_hash,
                WorkspaceInvitationModel.expires_at > now,
                WorkspaceInvitationModel.accepted_at.is_(None),
            )
            .first()
        )

    def accept_invitation(self, invitation_id: str) -> bool:
        inv = self.db.query(WorkspaceInvitationModel).filter(WorkspaceInvitationModel.id == invitation_id).first()
        if not inv:
            return False
        setattr(inv, "accepted_at", utc_now())
        self.db.commit()
        return True

    # ----------------- User Registration (Atomic) -----------------
    def register_user_atomic(
        self,
        email: str,
        password_hash: str,
        full_name: str,
        workspace_name: Optional[str] = None,
        invitation_code_hash: Optional[str] = None,
        cgu_version: Optional[str] = "2026-v1",
        privacy_version: Optional[str] = "2026-v1",
        language: str = "fr",
        theme: str = "dark",
        email_verified: bool = False,
    ) -> Tuple[UserModel, WorkspaceModel, str]:
        """
        Atomically registers a user, provisions either a joined workspace (via invite)
        or a new workspace (Owner), initial brand profile, and audits the registration.
        """
        email_clean = email.strip().lower()
        if self.get_user_by_email(email_clean):
            raise ValueError(f"Un compte avec l'adresse {email_clean} existe déjà.")

        now = utc_now()
        user_id = f"usr_{uuid.uuid4().hex[:12]}"

        user = UserModel(
            id=user_id,
            email=email_clean,
            password_hash=password_hash,
            full_name=full_name.strip(),
            display_name=full_name.strip().split()[0] if full_name.strip() else None,
            job_title="Membre de l'équipe",
            timezone="Europe/Paris",
            language=language,
            theme=theme,
            is_active=True,
            email_verified=email_verified,
            cgu_accepted_at=now if cgu_version else None,
            cgu_version=cgu_version,
            privacy_accepted_at=now if privacy_version else None,
            privacy_version=privacy_version,
            failed_login_attempts=0,
        )
        self.db.add(user)

        # Handle workspace assignment
        assigned_role = "Owner"
        if invitation_code_hash:
            inv = self.get_invitation_by_code_hash(invitation_code_hash)
            if not inv:
                raise ValueError("Code d'invitation invalide ou expiré.")
            target_ws = self.get_workspace(str(inv.workspace_id))
            if not target_ws:
                raise ValueError("Le workspace associé à l'invitation n'existe plus.")
            assigned_role = str(inv.role)
            self.add_workspace_member(workspace_id=str(target_ws.id), user_id=user_id, role=assigned_role)
            setattr(inv, "accepted_at", now)
            final_workspace = target_ws
        else:
            ws_id = f"ws_{uuid.uuid4().hex[:12]}"
            final_ws_name = workspace_name.strip() if workspace_name and workspace_name.strip() else f"Workspace {full_name.strip()}"
            final_workspace = WorkspaceModel(
                id=ws_id,
                name=final_ws_name,
                timezone="Europe/Paris",
                owner_id=user_id,
                is_demo=False,
            )
            self.db.add(final_workspace)
            self.add_workspace_member(workspace_id=ws_id, user_id=user_id, role="Owner")

            # Seed default brand profile
            bp = BrandProfileModel(
                id=f"bp_{uuid.uuid4().hex[:12]}",
                workspace_id=ws_id,
                version=1,
                audience=["Professionnels", "B2B Leaders", "Décideurs Tech"],
                voice="Expert, engageant, clair et orienté valeur.",
                pillars=["Innovation & Tendances", "Méthodologie & Best Practices", "Cas d'usage concrets"],
                prohibited_topics=["Allégations sans source", "Langage familier déplacé"],
                cta_policy={
                    "allowed_ctas": ["Donnez votre avis en commentaire", "Contactez notre équipe"],
                    "max_per_post": 1,
                },
            )
            self.db.add(bp)

            # Seed default LLM settings
            llm_settings = WorkspaceLLMSettingsModel(
                id=f"llm_cfg_{uuid.uuid4().hex[:12]}",
                workspace_id=ws_id,
                default_provider_id="nvidia",
                default_model_id="z-ai/glm-5.3-flash",
                default_temperature=0.2,
                task_overrides={},
                provider_settings={},
            )
            self.db.add(llm_settings)

        self.record_audit_log(
            user_id=user_id,
            workspace_id=str(final_workspace.id),
            event_type="user_registered",
            severity="INFO",
            details={
                "email": email_clean,
                "role": assigned_role,
                "via_invitation": bool(invitation_code_hash),
            },
        )

        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(final_workspace)
        return (user, final_workspace, assigned_role)

    # ----------------- Demo Workspaces (Ephemeral) -----------------
    def create_demo_workspace_session(
        self,
        duration_minutes: int = 120,
    ) -> Tuple[UserModel, WorkspaceModel, str]:
        """
        Creates an ephemeral, isolated workspace with rich pre-seeded data
        and auto-expiry for risk-free product evaluation.
        """
        now = utc_now()
        expires_at = now + timedelta(minutes=duration_minutes)
        suffix = uuid.uuid4().hex[:8]
        user_id = f"demo_usr_{suffix}"
        ws_id = f"ws_demo_{suffix}"

        user = UserModel(
            id=user_id,
            email=f"demo_{suffix}@demo.contentops.internal",
            password_hash=None,
            full_name="Visiteur Démo",
            display_name="Démo Invité",
            job_title="Evaluateur ContentOps",
            timezone="Europe/Paris",
            language="fr",
            theme="dark",
            is_active=True,
            email_verified=True,
            failed_login_attempts=0,
        )
        self.db.add(user)

        ws = WorkspaceModel(
            id=ws_id,
            name=f"Espace Démo ({suffix.upper()})",
            timezone="Europe/Paris",
            owner_id=user_id,
            is_demo=True,
            expires_at=expires_at,
        )
        self.db.add(ws)
        self.add_workspace_member(workspace_id=ws_id, user_id=user_id, role="Owner")

        # Pre-seed realistic brand profile
        bp = BrandProfileModel(
            id=f"bp_{uuid.uuid4().hex[:12]}",
            workspace_id=ws_id,
            version=1,
            audience=["Tech Leads", "Directeurs Marketing", "AI Practitioners"],
            voice="Analytique, visionnaire, mesuré et orienté retour sur investissement.",
            pillars=["Architecture des agents IA", "Content Engineering B2B", "Gouvernance & HITL"],
            prohibited_topics=["Conseils financiers", "Promesses irréalistes"],
            cta_policy={
                "allowed_ctas": ["Partagez votre retour d'expérience", "Découvrez notre livre blanc"],
                "max_per_post": 1,
            },
        )
        self.db.add(bp)

        # Pre-seed a realistic source
        source = ContentSourceModel(
            id=f"src_{uuid.uuid4().hex[:12]}",
            workspace_id=ws_id,
            type="url",
            canonical_url="https://contentops.internal/blog/ai-orchestration-2026",
            raw_content_ref="Synthèse prospective : orchestration multi-modèles et agents autonomes en 2026.",
            extracted_facts=[
                "La supervision humaine (HITL) réduit les hallucinations critiques de 94%",
                "Le routage dynamique multi-fournisseurs divise les coûts d'inférence par 3"
            ],
            provenance={"author": "ContentOps Research", "date": "2026-03"},
            status="ingested",
        )
        self.db.add(source)

        # Pre-seed a sample idea
        idea = IdeaModel(
            id=f"idea_{uuid.uuid4().hex[:12]}",
            workspace_id=ws_id,
            title="Pourquoi 2026 marque la fin des modèles monolithiques au profit d'agents spécialisés",
            angle="Comparer les architectures monolithiques coûteuses aux graphes d'agents avec garde-fous stricts.",
            pillar="Architecture des agents IA",
            audience="Tech Leads",
            evidence_refs=["https://contentops.internal/blog/ai-orchestration-2026"],
            novelty_score=0.88,
            relevance_score=0.92,
            effort_score=0.40,
            total_score=0.85,
            priority="high",
            risks=["Éviter d'attaquer directement un modèle particulier"],
            status="IDEA",
        )
        self.db.add(idea)

        # Pre-seed LLM Settings
        llm_settings = WorkspaceLLMSettingsModel(
            id=f"llm_cfg_{uuid.uuid4().hex[:12]}",
            workspace_id=ws_id,
            default_provider_id="nvidia",
            default_model_id="z-ai/glm-5.3-flash",
            default_temperature=0.2,
            task_overrides={},
            provider_settings={},
        )
        self.db.add(llm_settings)

        self.record_audit_log(
            user_id=user_id,
            workspace_id=ws_id,
            event_type="demo_workspace_created",
            severity="INFO",
            details={"expires_at": expires_at.isoformat(), "is_demo": True},
        )

        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(ws)
        return (user, ws, "Owner")

    def cleanup_expired_demo_workspaces(self) -> int:
        now = utc_now()
        expired = (
            self.db.query(WorkspaceModel)
            .filter(
                WorkspaceModel.is_demo.is_(True),
                WorkspaceModel.expires_at < now,
            )
            .all()
        )
        count = len(expired)
        for ws in expired:
            self.db.delete(ws)
        if count > 0:
            self.db.commit()
        return count

    # ----------------- Bootstrapping Defaults -----------------
    def ensure_default_users(self) -> None:
        """Ensures default seed users exist for seamless development & tests."""
        from packages.security.passwords import hash_password
        default_pwd_hash = hash_password("DevPassword2026!")

        user_martial = self.get_user("owner_martial")
        if not user_martial:
            self.create_user(
                user_id="owner_martial",
                email="martial@contentops.internal",
                password_hash=default_pwd_hash,
                full_name="Martial Martial",
                display_name="Martial (CCO)",
                job_title="Chief Content Officer",
                timezone="Europe/Paris",
                language="fr",
                theme="dark",
                email_verified=True,
                notification_preferences={
                    "email_critical_alerts": True,
                    "browser_push": True,
                    "weekly_digest": True,
                    "notify_on_approval": True,
                },
                ui_preferences={
                    "density": "comfortable",
                    "default_view": "calendar",
                },
            )
            self.add_workspace_member("ws_default", "owner_martial", "Owner")
        else:
            setattr(user_martial, "email_verified", True)
            if not user_martial.password_hash:
                setattr(user_martial, "password_hash", default_pwd_hash)
            self.db.commit()

        user_dev = self.get_user("dev_user")
        if not user_dev:
            self.create_user(
                user_id="dev_user",
                email="dev@contentops.internal",
                password_hash=default_pwd_hash,
                full_name="Dev User",
                display_name="Dev Contributor",
                job_title="Senior Content Strategist",
                timezone="UTC",
                language="fr",
                theme="dark",
                email_verified=True,
                notification_preferences={
                    "email_critical_alerts": True,
                    "browser_push": False,
                    "weekly_digest": True,
                    "notify_on_approval": True,
                },
                ui_preferences={
                    "density": "comfortable",
                    "default_view": "inbox",
                },
            )
            self.add_workspace_member("ws_default", "dev_user", "Editor")
        else:
            setattr(user_dev, "email_verified", True)
            if not user_dev.password_hash:
                setattr(user_dev, "password_hash", default_pwd_hash)
            self.db.commit()

        # Also ensure login_test has email_verified=True if present
        login_test = self.get_user_by_email("login_test@contentops.internal")
        if login_test and not login_test.email_verified:
            setattr(login_test, "email_verified", True)
            self.db.commit()




