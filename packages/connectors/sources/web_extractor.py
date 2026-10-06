import re
import hashlib
from typing import Dict, Any, List
from datetime import datetime


class WebExtractorConnector:
    """
    Extracts, normalizes, and sanitizes untrusted external sources (URLs, notes, text)
    strictly mitigating prompt injection risks as defined in PRD Section 7.
    """

    SUSPICIOUS_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
        re.compile(r"you\s+must\s+now\s+act\s+as", re.IGNORECASE),
        re.compile(r"<script.*?>.*?</script>", re.IGNORECASE),
        re.compile(r"\{\{.*?\}\}", re.IGNORECASE),  # template injections
    ]

    @classmethod
    def sanitize_untrusted_input(cls, text: str) -> str:
        """
        Neutralizes potential prompt injection markers and tags in untrusted content.
        """
        sanitized = text
        for pattern in cls.SUSPICIOUS_PATTERNS:
            sanitized = pattern.sub("[FILTERED_UNTRUSTED_INSTRUCTION]", sanitized)
        return sanitized

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
        workspace_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Normalizes source data, tags provenance, computes deduplication hash.
        """
        sanitized_content = cls.sanitize_untrusted_input(content)
        content_hash = hashlib.sha256(sanitized_content.strip().encode("utf-8")).hexdigest()
        facts = cls.extract_facts(sanitized_content)

        return {
            "workspace_id": workspace_id,
            "type": source_type,
            "canonical_url": url,
            "raw_content_ref": f"storage/sources/{content_hash[:16]}.txt",
            "extracted_facts": facts,
            "provenance": {
                "hash": content_hash,
                "author": author or "Unknown",
                "extracted_at": datetime.utcnow().isoformat(),
                "url": url,
                "untrusted_sanitized": True
            },
            "status": "ingested"
        }
