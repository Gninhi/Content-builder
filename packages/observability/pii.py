import re


class PIIRedactor:
    """
    Redacts sensitive personal information (PII) and secret API keys/tokens
    before logging or sending to tracing systems (PRD Section 3.2 & 7).
    """

    PATTERNS = [
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), "[REDACTED_EMAIL]"),
        (re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), "[REDACTED_PHONE]"),
        (re.compile(r'(?i)(bearer\s+|api[_-]?key[\s:=]+|secret[\s:=]+)(["\']?[A-Za-z0-9_\-\.]{16,}["\']?)'), r"\1[REDACTED_SECRET]"),
        (re.compile(r'AIza[A-Za-z0-9_\-]{30,}'), "[REDACTED_GOOGLE_KEY]"),
        (re.compile(r'pk-lf-[A-Za-z0-9_\-]{16,}'), "[REDACTED_LANGFUSE_PUBLIC_KEY]"),
        (re.compile(r'sk-lf-[A-Za-z0-9_\-]{16,}'), "[REDACTED_LANGFUSE_SECRET_KEY]"),
        (re.compile(r'nvapi-[A-Za-z0-9_\-]{16,}'), "[REDACTED_NVIDIA_KEY]"),
        (re.compile(r'tvly-[A-Za-z0-9_\-]{16,}'), "[REDACTED_TAVILY_KEY]"),
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.PATTERNS:
            result = pattern.sub(replacement, result)
        return result
