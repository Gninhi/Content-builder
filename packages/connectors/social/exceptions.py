from typing import Optional


class SocialConnectorError(Exception):
    """Base exception for all social connectors and publishers."""
    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.provider = provider


class SocialAuthenticationError(SocialConnectorError):
    """Raised when authentication credentials (OAuth token) are missing, invalid or expired."""
    pass


class SocialPermissionError(SocialConnectorError):
    """Raised when client lacks necessary OAuth scopes or endpoint access (HTTP 403)."""
    pass


class SocialRateLimitError(SocialConnectorError):
    """Raised when rate limit is exceeded (HTTP 429). Includes retry-after if available."""
    def __init__(self, message: str, provider: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(message, provider=provider)
        self.retry_after = retry_after


class SocialBillingError(SocialConnectorError):
    """Raised when API tier or credits are exhausted (HTTP 402/403 credit errors). Non-retryable."""
    pass


class SocialDuplicateError(SocialConnectorError):
    """Raised when social platform rejects the post as a duplicate."""
    pass


class SocialNetworkError(SocialConnectorError):
    """Raised on connection timeout or network level failures before response."""
    pass


class SocialPublishUnknownError(SocialConnectorError):
    """
    Raised when publication status cannot be confirmed after network transmission.
    Requires at-most-once reconciliation instead of blind retries.
    """
    pass


class TokenExpiringSoonError(SocialConnectorError):
    """Raised when token expiration is within safety threshold (e.g. 7 days). Reconnection required."""
    pass


class TokenRefreshError(SocialConnectorError):
    """Raised when automatic OAuth token refresh fails."""
    pass
