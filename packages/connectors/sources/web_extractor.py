import re
import hashlib
from typing import Dict, Any, List
from datetime import datetime, timezone
from packages.security.prompt_injection import PromptInjectionGuard


class WebExtractorConnector:
    """
    Extracts, normalizes, and sanitizes untrusted external sources (URLs, notes, text)
    strictly mitigating prompt injection risks via centralized PromptInjectionGuard.
    """

    @classmethod
    def sanitize_untrusted_input(cls, text: str) -> str:
        """
        Delegates to centralized security sanitizer to neutralize potential prompt injection markers,
        zero-width hidden instructions, and boundary breakout attempts.
        """
        return PromptInjectionGuard.sanitize_untrusted_input(text)

    @classmethod
    def wrap_untrusted_content(cls, content: str, source_id: str = "unknown") -> str:
        """
        Encapsulates untrusted external text in strict boundary delimiters
        ensuring it is treated strictly as passive data and never as instructions.
        """
        sanitized = cls.sanitize_untrusted_input(content)
        return f'<untrusted_external_data source_id="{source_id}" role="passive_data_only">\n{sanitized}\n</untrusted_external_data>'

    @classmethod
    def extract_facts(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extracts key sentences and facts from text for verification and citation tracking.
        """
        sentences = [s.strip() for s in re.split(r'[.\n!?;]', text) if len(s.strip()) > 25]
        facts = []
        for idx, sentence in enumerate(sentences[:10]):
            has_metric = bool(re.search(r'\d+', sentence))
            facts.append({
                "fact_id": f"fact_{idx + 1}",
                "claim": sentence,
                "contains_metrics": has_metric,
                "confidence": 0.9 if has_metric else 0.8
            })
        return facts

    @classmethod
    def process_source(
        cls,
        source_type: str,
        content: str,
        url: str | None = None,
        author: str | None = None,
        workspace_id: str = "default",
        extraction_status: str = "ingested",
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Normalizes source data, tags provenance, computes deduplication hash.
        Never fabricates placeholder S3 URIs or synthetic text.
        """
        sanitized_content = cls.sanitize_untrusted_input(content or "")
        content_hash = hashlib.sha256(sanitized_content.strip().encode("utf-8")).hexdigest()
        facts = cls.extract_facts(sanitized_content)
        meta = metadata or {}

        return {
            "workspace_id": workspace_id,
            "type": source_type,
            "canonical_url": meta.get("canonical_url") or url,
            "raw_content_ref": f"sha256:{content_hash}",
            "extracted_facts": facts,
            "provenance": {
                "hash": content_hash,
                "author": author or meta.get("author") or "Unknown",
                "title": meta.get("title"),
                "published_date": meta.get("published_date"),
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "url": url,
                "extraction_status": extraction_status,
                "extracted_chars": len(sanitized_content),
                "content_preview": sanitized_content[:2000],
                "untrusted_sanitized": True,
            },
            "status": extraction_status,
        }
