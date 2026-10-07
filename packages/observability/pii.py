import re


class PIIRedactor:
    """
    Redacts sensitive personal information (PII) and secret API keys/tokens
    before logging or sending to tracing systems (PRD Section 3.2 & 7).
    Includes dedicated masking for LinkedIn, X (Twitter), OAuth codes, and PKCE tokens.
    """

    PATTERNS = [
        # PII: Email & Phone
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), "[REDACTED_EMAIL]"),
        (re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), "[REDACTED_PHONE]"),
        # Standard Bearer / Secrets
        (re.compile(r'(?i)(bearer\s+|api[_-]?key[\s:=]+|secret[\s:=]+)(["\']?[A-Za-z0-9_\-\.]{16,}["\']?)'), r"\1[REDACTED_SECRET]"),
        # Google & Langfuse API keys
        (re.compile(r'AIza[A-Za-z0-9_\-]{30,}'), "[REDACTED_GOOGLE_KEY]"),
        (re.compile(r'pk-lf-[A-Za-z0-9_\-]{16,}'), "[REDACTED_LANGFUSE_PUBLIC_KEY]"),
        (re.compile(r'sk-lf-[A-Za-z0-9_\-]{16,}'), "[REDACTED_LANGFUSE_SECRET_KEY]"),
        (re.compile(r'nvapi-[A-Za-z0-9_\-]{16,}'), "[REDACTED_NVIDIA_KEY]"),
        (re.compile(r'tvly-[A-Za-z0-9_\-]{16,}'), "[REDACTED_TAVILY_KEY]"),
        # LinkedIn Member / Access Tokens (starts with AQ and has 60+ chars)
        (re.compile(r'\bAQ[A-Za-z0-9_\-]{40,}\b'), "[REDACTED_LINKEDIN_TOKEN]"),
        # X / Twitter OAuth 2.0 User Tokens and Refresh Tokens
        (re.compile(r'(?i)(x[_-]?(?:access[_-]?token|refresh[_-]?token|client[_-]?secret)[\s:=]+)(["\']?[A-Za-z0-9_\-\.]{20,}["\']?)'), r"\1[REDACTED_X_TOKEN]"),
        # PKCE code_verifier & code_challenge
        (re.compile(r'(?i)(code[_-]verifier[\s:=]+)(["\']?[A-Za-z0-9_\-\.]{32,}["\']?)'), r"\1[REDACTED_PKCE_VERIFIER]"),
        (re.compile(r'(?i)(code[_-]challenge[\s:=]+)(["\']?[A-Za-z0-9_\-\.]{32,}["\']?)'), r"\1[REDACTED_PKCE_CHALLENGE]"),
        # OAuth query parameters in logs (code=..., state=...)
        (re.compile(r'(?i)([?&]code=)[A-Za-z0-9_\-\.]{16,}'), r"\1[REDACTED_OAUTH_CODE]"),
        (re.compile(r'(?i)([?&]state=)[A-Za-z0-9_\-\.]{16,}'), r"\1[REDACTED_OAUTH_STATE]"),
        # Standard JWT pattern (header.payload.signature)
        (re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-.+/=]{10,}\b'), "[REDACTED_JWT]"),
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.PATTERNS:
            result = pattern.sub(replacement, result)
        return result
