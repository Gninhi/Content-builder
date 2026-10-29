import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from infra.db.models import (
    BrandProfileModel,
    ApprovalModel,
    ContentVariantModel,
    ContentPackageModel,
    ContentBriefModel,
    ContentSourceModel,
    SignalModel,
    VeilleRunModel,
)

logger = logging.getLogger(__name__)


class ShortTermGraphMemory:
    """
    Governs short-term per-run / per-thread LangGraph state (Section 9.1).
    Enforces workspace-prefixed deterministic thread_ids and prunes heavy transient payloads.
    """

    @staticmethod
    def build_thread_id(workspace_id: str, workflow: str, entity_id: str) -> str:
        ws = (workspace_id or "").strip()
        wf = (workflow or "").strip()
        ent = (entity_id or "").strip()
        if not ws or not wf or not ent:
            raise ValueError("workspace_id, workflow, and entity_id must all be non-empty to build a safe thread_id.")
        return f"{ws}:{wf}:{ent}"

    @staticmethod
    def validate_thread_ownership(thread_id: str, workspace_id: str) -> bool:
        if not thread_id or not workspace_id:
            return False
        return thread_id.startswith(f"{workspace_id.strip()}:")

    @staticmethod
    def prune_state_for_checkpoint(state: Dict[str, Any], max_text_len: int = 3000) -> Dict[str, Any]:
        """Removes raw HTML blobs and truncates oversized text buffers before checkpointing."""
        pruned = dict(state)
        pruned.pop("raw_html", None)
        pruned.pop("raw_bytes", None)
        if "raw_sources" in pruned and isinstance(pruned["raw_sources"], list):
            clean_sources = []
            for s in pruned["raw_sources"]:
                if isinstance(s, dict):
                    s_copy = dict(s)
                    s_copy.pop("raw_html", None)
                    if "content" in s_copy and isinstance(s_copy["content"], str):
                        s_copy["content"] = s_copy["content"][:max_text_len]
                    clean_sources.append(s_copy)
            pruned["raw_sources"] = clean_sources
        return pruned


class WorkspaceMemoryService:
    """
    Long-term workspace editorial memory service (Section 9.2).
    Strictly scoped by `workspace_id`. Never auto-mutates `BrandProfileModel` (ADR 0006).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_editorial_memory(self, workspace_id: str, max_feedback_items: int = 5) -> Dict[str, Any]:
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("workspace_id is required to access WorkspaceMemoryService.")

        ws_id = str(workspace_id).strip()
        bp = (
            self.db.query(BrandProfileModel)
            .filter(BrandProfileModel.workspace_id == ws_id)
            .order_by(BrandProfileModel.version.desc())
            .first()
        )

        # Fetch recent human review decisions scoped to this workspace
        recent_approvals = (
            self.db.query(ApprovalModel)
            .join(ContentVariantModel, ApprovalModel.variant_id == ContentVariantModel.id)
            .join(ContentPackageModel, ContentVariantModel.package_id == ContentPackageModel.id)
            .join(ContentBriefModel, ContentPackageModel.brief_id == ContentBriefModel.id)
            .filter(ContentBriefModel.workspace_id == ws_id)
            .order_by(ApprovalModel.reviewed_at.desc())
            .limit(max_feedback_items * 2)
            .all()
        )

        approved_notes: List[str] = []
        rejection_or_rewrite_notes: List[str] = []
        for appr in recent_approvals:
            fb = str(appr.feedback or "").strip()
            if not fb:
                continue
            if appr.decision == "approve" and len(approved_notes) < max_feedback_items:
                approved_notes.append(fb[:240])
            elif appr.decision in ("reject", "rewrite", "request_rewrite") and len(rejection_or_rewrite_notes) < max_feedback_items:
                rejection_or_rewrite_notes.append(fb[:240])

        return {
            "workspace_id": ws_id,
            "brand_voice": str(bp.voice) if bp else "Expert et direct",
            "audience": list(bp.audience or []) if bp else [],
            "pillars": list(bp.pillars or []) if bp else [],
            "prohibited_topics": list(bp.prohibited_topics or []) if bp else [],
            "cta_policy": dict(bp.cta_policy or {}) if bp else {},
            "recent_approved_feedback": approved_notes,
            "recent_correction_feedback": rejection_or_rewrite_notes,
        }

    def propose_brand_profile_adjustment(
        self,
        workspace_id: str,
        proposed_voice: Optional[str] = None,
        proposed_pillars: Optional[List[str]] = None,
        proposed_prohibited_topics: Optional[List[str]] = None,
        rationale: str = "",
    ) -> Dict[str, Any]:
        """
        Propositional learning (ADR 0006 & Section 9.2):
        Generates a non-destructive recommendation for human validation without mutating BrandProfileModel.
        """
        current = self.get_editorial_memory(workspace_id)
        return {
            "workspace_id": workspace_id,
            "status": "PROPOSED_FOR_HUMAN_REVIEW",
            "auto_applied": False,
            "current_voice": current["brand_voice"],
            "proposed_voice": proposed_voice or current["brand_voice"],
            "proposed_pillars": proposed_pillars if proposed_pillars is not None else current["pillars"],
            "proposed_prohibited_topics": (
                proposed_prohibited_topics
                if proposed_prohibited_topics is not None
                else current["prohibited_topics"]
            ),
            "rationale": rationale or "Suggestion issue de l'historique de validation éditoriale.",
        }


class EvidenceMemoryService:
    """
    Documentary and monitoring evidence memory service (Section 9.3 & 9.4).
    Strictly isolated by `workspace_id` with deduplication and retention helpers.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_verified_evidence_dossier(
        self,
        workspace_id: str,
        min_score: float = 3.2,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("workspace_id is required to access EvidenceMemoryService.")
        ws_id = str(workspace_id).strip()

        seen_urls = set()
        dossier: List[Dict[str, Any]] = []

        # 1. Qualified signals for this workspace
        signals = (
            self.db.query(SignalModel)
            .filter(
                SignalModel.workspace_id == ws_id,
                SignalModel.qualification_score >= min_score,
            )
            .order_by(SignalModel.qualification_score.desc(), SignalModel.created_at.desc())
            .limit(limit)
            .all()
        )
        for sig in signals:
            url = str(sig.canonical_url or "").strip()
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            dossier.append(
                {
                    "source_type": "signal",
                    "id": sig.id,
                    "url": url,
                    "title": sig.title,
                    "summary": sig.summary,
                    "facts": list(sig.facts or []),
                    "executive_takeaway": sig.executive_takeaway,
                    "score": float(sig.qualification_score or 0.0),
                    "enrichment_status": getattr(sig, "enrichment_status", "deterministic_only"),
                }
            )

        # 2. Extracted documentary sources for this workspace
        sources = (
            self.db.query(ContentSourceModel)
            .filter(ContentSourceModel.workspace_id == ws_id)
            .order_by(ContentSourceModel.created_at.desc())
            .limit(limit)
            .all()
        )
        for src in sources:
            url = str(src.canonical_url or "").strip()
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            facts = list(src.extracted_facts or [])
            if not facts:
                continue
            dossier.append(
                {
                    "source_type": "content_source",
                    "id": src.id,
                    "url": url,
                    "title": url,
                    "summary": " ".join(str(f) for f in facts[:2])[:400],
                    "facts": facts,
                    "key_quotes": [],
                    "score": float(src.trust_score or 1.0) * 4.0,
                    "enrichment_status": "EXTRACTED",
                }
            )

        return dossier[:limit]

    def purge_expired_runs(self, workspace_id: str, retention_days: int = 90) -> int:
        """
        Purges VeilleRunModel records older than `retention_days` for the given workspace
        while strictly preserving immutable editorial audit records (Approvals, PublishJobs).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))
        # Handle naive UTC datetimes stored in SQLite
        cutoff_naive = cutoff.replace(tzinfo=None)
        deleted = (
            self.db.query(VeilleRunModel)
            .filter(
                VeilleRunModel.workspace_id == workspace_id,
                VeilleRunModel.started_at < cutoff_naive,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return int(deleted or 0)
