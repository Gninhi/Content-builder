import re
import logging
from typing import Tuple, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SUSPICIOUS_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|prompts)",
    r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|rules)",
    r"you\s+are\s+now\s+(an?\s+)?(unrestricted|evil|dan|new\s+role)",
    r"you\s+must\s+now\s+act\s+as",
    r"system\s*:\s*(you|override)",
    r"new\s+system\s+prompt\s*:",
    r"reveal\s+(your\s+)?(api_key|secrets?|passwords?|tokens?)",
    r"publish\s+without\s+(approval|review|validation)",
    r"delete\s+(all\s+)?(data|database|records)",
    r"bypass\s+(all\s+)?(guardrails|filters|security)",
    r"</?untrusted(?:_external_data|_content)?>",
    r"<script.*?>.*?</script>",
    r"\{\{.*?\}\}",
    r"(?:call\s+tool|execute\s+command|eval\s*\()",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]


def sanitize_untrusted_input_filtered(text: str) -> str:
    """
    Centralized sanitizer: strips zero-width hidden characters, replaces hostile instructions
    with [FILTERED_UNTRUSTED_INSTRUCTION], and encodes XML brackets to prevent boundary breakouts.
    """
    if not text:
        return ""
    # Strip zero-width characters and directional overrides used to hide instructions
    cleaned = re.sub(r"[\u200B-\u200D\uFEFF\u202A-\u202E]", "", text)
    for pattern in COMPILED_PATTERNS:
        cleaned = pattern.sub("[FILTERED_UNTRUSTED_INSTRUCTION]", cleaned)
    # Neutralize residual XML tag delimiters that could break encapsulation
    cleaned = cleaned.replace("<", "&lt;").replace(">", "&gt;")
    return cleaned


def wrap_untrusted_data(content: str, origin: str, timestamp: Optional[str] = None) -> str:
    """
    Encapsulates external web data in isolated untrusted data tags.
    Ensures LLM instruction interpreters treat this content solely as analytical data.
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    # Strip any attempt to close the tag from within the content
    sanitized = content.replace("</untrusted_external_data>", "[escaped_tag]")
    return f'<untrusted_external_data origin="{origin}" collected_at="{ts}">\n{sanitized}\n</untrusted_external_data>'


def detect_suspicious_instructions(text: str) -> Tuple[bool, List[str]]:
    """
    Detects known indirect prompt injection patterns in retrieved external content.
    Returns (is_suspicious, matched_patterns).
    """
    if not text:
        return False, []

    matched = []
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            matched.append(match.group(0))

    if matched:
        logger.warning(f"Potential indirect prompt injection detected: {matched[:3]}")

    return len(matched) > 0, matched


def sanitize_untrusted_text(text: str) -> str:
    """
    Sanitizes raw text to neutralize prompt injection vectors before agent processing:
    - Normalizes invisible unicode characters (zero-width spaces, directional overrides)
    - Replaces explicit jailbreak markers
    """
    if not text:
        return ""

    # Strip zero-width characters and directional overrides used to hide instructions
    cleaned = re.sub(r"[\u200B-\u200D\uFEFF\u202A-\u202E]", "", text)

    # Flag and defang suspicious phrases
    is_suspicious, matches = detect_suspicious_instructions(cleaned)
    if is_suspicious:
        for m in matches:
            cleaned = cleaned.replace(m, f"[DEFANGED_PROMPT_INJECTION: {m}]")

    return cleaned


class PromptInjectionGuard:
    """Convenience class wrapper for prompt injection defense functions."""

    @staticmethod
    def wrap(content: str, origin: str, timestamp: Optional[str] = None) -> str:
        return wrap_untrusted_data(content, origin, timestamp)

    @staticmethod
    def detect(text: str) -> Tuple[bool, List[str]]:
        return detect_suspicious_instructions(text)

    @staticmethod
    def defang_text(text: str) -> str:
        return sanitize_untrusted_text(text)

    @staticmethod
    def sanitize_untrusted_input(text: str) -> str:
        return sanitize_untrusted_input_filtered(text)

    @staticmethod
    def sanitize_for_prompt(text: str, origin: str) -> str:
        cleaned = sanitize_untrusted_text(text)
        return wrap_untrusted_data(cleaned, origin)
