"""
Security exceptions module for ContentOps Harness.
"""


class SecurityContextError(RuntimeError):
    """Raised when security isolation, RLS context, or multi-tenant boundary fails."""
    pass
