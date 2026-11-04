"""
Prompt defense re-export module providing PromptInjectionGuard alias.
"""
from packages.security.prompt_injection import (
    PromptInjectionGuard,
    sanitize_untrusted_input_filtered,
    wrap_untrusted_data,
    detect_suspicious_instructions,
    sanitize_untrusted_text,
)

__all__ = [
    "PromptInjectionGuard",
    "sanitize_untrusted_input_filtered",
    "wrap_untrusted_data",
    "detect_suspicious_instructions",
    "sanitize_untrusted_text",
]
