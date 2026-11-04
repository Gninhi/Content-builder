"""
Backward-compatibility re-export module for SanitizedLangfuseCallbackHandler.
The canonical definition has moved to packages.observability.callbacks.langfuse (ANOM-04 / ARCH-02).
"""
from packages.observability.callbacks.langfuse import SanitizedLangfuseCallbackHandler

__all__ = ["SanitizedLangfuseCallbackHandler"]
