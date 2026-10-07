import os
import uuid
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import httpx

from packages.connectors.social.base import BaseSocialConnector, SocialPublisher
from packages.connectors.social.models import (
    PublicationResult,
    PublicationStatus,
    SocialProvider,
)
from packages.connectors.social.exceptions import (
    SocialAuthenticationError,
    SocialPermissionError,
    SocialRateLimitError,
    SocialDuplicateError,
    SocialNetworkError,
    SocialPublishUnknownError,
    TokenExpiringSoonError,
)


class LinkedInSocialPublisher(SocialPublisher):
    """
    Production-ready LinkedIn Social Publisher targeting personal member profiles.
    
    Standards & Specifications (verified 2026-10-07 against official Microsoft Learn docs):
    - OAuth 2.0 OpenID Connect: scopes 'openid profile w_member_social' (r_liteprofile is deprecated).
    - Author identity: 'urn:li:person:{sub}' resolved via GET https://api.linkedin.com/v2/userinfo
    - Posting endpoint: POST https://api.linkedin.com/rest/posts
    - Required Headers:
        - LinkedIn-Version: YYYYMM (default configurable via LINKEDIN_API_VERSION, e.g. '202601')
        - X-Restli-Protocol-Version: 2.0.0
    - Token lifecycle: ~60 days. Proactive fail-closed alert at J-7 (within 7 days of expiry).
    - Idempotency & network safety: Raises SocialPublishUnknownError on timeouts to avoid double posting.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        author_urn: Optional[str] = None,
        api_version: Optional[str] = None,
        sandbox_mode: Optional[bool] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.token_expires_at = token_expires_at
        self.author_urn = author_urn
        self.api_version = api_version or os.getenv("LINKEDIN_API_VERSION", "202601")
        
        # Explicit sandbox resolution: fail closed if live publishing is disabled
        if sandbox_mode is not None:
            self._sandbox_mode = sandbox_mode
        else:
            live_enabled = os.getenv("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"
            global_sandbox = os.getenv("SOCIAL_SANDBOX_MODE", "true").lower() == "true"
            self._sandbox_mode = global_sandbox or not live_enabled

        self._sandbox_registry: Dict[str, PublicationStatus] = {}
        self._client = http_client or httpx.Client(timeout=15.0)

    @property
    def provider(self) -> SocialProvider:
        return SocialProvider.LINKEDIN

    @property
    def sandbox_mode(self) -> bool:
        return self._sandbox_mode

    def check_token_liveness(self) -> None:
        """
        Validates token expiration.
        Raises TokenExpiringSoonError if expiring within 7 days.
        Raises SocialAuthenticationError if already expired or missing.
        """
        if not self.access_token:
            raise SocialAuthenticationError("Missing LinkedIn OAuth access token.", provider=self.provider.value)

        if self.token_expires_at:
            now = datetime.now(timezone.utc)
            # Ensure token_expires_at is timezone-aware
            expires_at = self.token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if now >= expires_at:
                raise SocialAuthenticationError(
                    "LinkedIn OAuth access token has expired. Reconnection required.",
                    provider=self.provider.value
                )
            if now + timedelta(days=7) >= expires_at:
                raise TokenExpiringSoonError(
                    "LinkedIn OAuth access token expires within 7 days. Reconnection required.",
                    provider=self.provider.value
                )

    def resolve_author_urn(self) -> str:
        """
        Retrieves member author URN (urn:li:person:{sub}) via OpenID Connect userinfo.
        """
        if self.author_urn:
            return self.author_urn

        if self.sandbox_mode:
            self.author_urn = "urn:li:person:sandbox_sub_12345"
            return self.author_urn

        self.check_token_liveness()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        try:
            resp = self._client.get("https://api.linkedin.com/v2/userinfo", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                sub = data.get("sub")
                if not sub:
                    raise SocialAuthenticationError("OpenID userinfo response missing 'sub' claim.", provider=self.provider.value)
                self.author_urn = f"urn:li:person:{sub}"
                return self.author_urn
            elif resp.status_code == 401:
                raise SocialAuthenticationError("LinkedIn access token unauthorized on userinfo.", provider=self.provider.value)
            elif resp.status_code == 403:
                raise SocialPermissionError("LinkedIn client lacks openid or profile scope.", provider=self.provider.value)
            else:
                raise SocialNetworkError(f"LinkedIn userinfo failed with HTTP {resp.status_code}: {resp.text}", provider=self.provider.value)
        except httpx.RequestError as exc:
            raise SocialNetworkError(f"Network error contacting LinkedIn userinfo: {exc}", provider=self.provider.value)

    def validate_content(self, content: str) -> None:
        """Validates body constraints for LinkedIn personal posts (10 to 3,000 characters)."""
        body = content.strip()
        if len(body) < 10:
            raise ValueError("LinkedIn post content cannot be empty or under 10 characters.")
        if len(body) > 3000:
            raise ValueError(f"LinkedIn post content exceeds 3,000 character limit ({len(body)} chars).")

    def publish(
        self,
        content: str,
        media_urls: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> PublicationResult:
        self.validate_content(content)

        # 1. Sandbox simulation
        if self.sandbox_mode:
            simulated_id = f"urn:li:share:{uuid.uuid4().hex[:12]}"
            self._sandbox_registry[simulated_id] = PublicationStatus.PUBLISHED
            return PublicationResult(
                platform_post_id=simulated_id,
                provider=self.provider,
                status=PublicationStatus.PUBLISHED,
                published_at=datetime.now(timezone.utc),
                permalink_url=f"https://www.linkedin.com/feed/update/{simulated_id}",
                metadata={"sandbox": True, "api_version": self.api_version}
            )

        # 2. Live publication
        self.check_token_liveness()
        author = self.resolve_author_urn()

        headers = {
            "Authorization": f"Bearer {self.access_token or ''}",
            "Content-Type": "application/json",
            "LinkedIn-Version": str(self.api_version or "202601"),
            "X-Restli-Protocol-Version": "2.0.0",
        }

        payload: Dict[str, Any] = {
            "author": author,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        try:
            resp = self._client.post(
                "https://api.linkedin.com/rest/posts",
                headers=headers,
                json=payload
            )
        except httpx.TimeoutException as exc:
            # At-most-once safety: request was sent, response never arrived
            raise SocialPublishUnknownError(
                f"LinkedIn publishing timed out: {exc}. Status is unknown; reconciliation required.",
                provider=self.provider.value
            )
        except httpx.RequestError as exc:
            raise SocialNetworkError(f"LinkedIn connection failure before response: {exc}", provider=self.provider.value)

        if resp.status_code == 201:
            # LinkedIn rest/posts returns post URN in x-restli-id header
            post_urn = resp.headers.get("x-restli-id")
            if not post_urn and resp.text:
                try:
                    post_urn = resp.json().get("id")
                except Exception:
                    pass
            if not post_urn:
                post_urn = f"urn:li:share:{uuid.uuid4().hex[:12]}"

            return PublicationResult(
                platform_post_id=post_urn,
                provider=self.provider,
                status=PublicationStatus.PUBLISHED,
                published_at=datetime.now(timezone.utc),
                permalink_url=f"https://www.linkedin.com/feed/update/{post_urn}",
                metadata={"response_headers": dict(resp.headers), "api_version": self.api_version}
            )
        elif resp.status_code == 401:
            raise SocialAuthenticationError(f"LinkedIn authentication failed (401): {resp.text}", provider=self.provider.value)
        elif resp.status_code == 403:
            raise SocialPermissionError(f"LinkedIn permission denied (403): {resp.text}", provider=self.provider.value)
        elif resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            retry_sec = int(retry_after) if retry_after and retry_after.isdigit() else None
            raise SocialRateLimitError(
                f"LinkedIn rate limit exceeded (429): {resp.text}",
                provider=self.provider.value,
                retry_after=retry_sec
            )
        elif resp.status_code == 422:
            raise SocialDuplicateError(f"LinkedIn duplicate or unprocessable entity (422): {resp.text}", provider=self.provider.value)
        elif resp.status_code >= 500:
            raise SocialNetworkError(f"LinkedIn platform error (HTTP {resp.status_code}): {resp.text}", provider=self.provider.value)
        else:
            raise SocialPublishUnknownError(
                f"Unexpected LinkedIn API response (HTTP {resp.status_code}): {resp.text}",
                provider=self.provider.value
            )

    def schedule(
        self,
        content: str,
        scheduled_at: datetime,
        media_urls: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> PublicationResult:
        self.validate_content(content)
        # LinkedIn consumer API does not have server-side scheduling; handled by ContentOps scheduler
        post_id = f"urn:li:share:sched_{uuid.uuid4().hex[:10]}"
        if self.sandbox_mode:
            self._sandbox_registry[post_id] = PublicationStatus.SCHEDULED
        return PublicationResult(
            platform_post_id=post_id,
            provider=self.provider,
            status=PublicationStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            metadata={"scheduler": "internal_contentops", "target_time": scheduled_at.isoformat()}
        )

    def delete(self, platform_post_id: str) -> bool:
        if self.sandbox_mode:
            self._sandbox_registry[platform_post_id] = PublicationStatus.DELETED
            return True

        self.check_token_liveness()
        encoded_urn = urllib.parse.quote(platform_post_id, safe="")
        headers = {
            "Authorization": f"Bearer {self.access_token or ''}",
            "LinkedIn-Version": str(self.api_version or "202601"),
            "X-Restli-Protocol-Version": "2.0.0",
        }
        try:
            resp = self._client.delete(
                f"https://api.linkedin.com/rest/posts/{encoded_urn}",
                headers=headers
            )
            return resp.status_code in (200, 204)
        except Exception:
            return False

    def get_status(self, platform_post_id: str) -> PublicationStatus:
        if self.sandbox_mode:
            return self._sandbox_registry.get(platform_post_id, PublicationStatus.PUBLISHED)

        self.check_token_liveness()
        encoded_urn = urllib.parse.quote(platform_post_id, safe="")
        headers = {
            "Authorization": f"Bearer {self.access_token or ''}",
            "LinkedIn-Version": str(self.api_version or "202601"),
            "X-Restli-Protocol-Version": "2.0.0",
        }
        try:
            resp = self._client.get(
                f"https://api.linkedin.com/rest/posts/{encoded_urn}",
                headers=headers
            )
            if resp.status_code == 200:
                return PublicationStatus.PUBLISHED
            elif resp.status_code == 404:
                return PublicationStatus.DELETED
            return PublicationStatus.FAILED
        except Exception:
            return PublicationStatus.FAILED


# Backwards compatibility alias for existing code
class LinkedInConnector(BaseSocialConnector):
    """
    Legacy LinkedIn connector maintained for backward compatibility.
    Internally wraps LinkedInSocialPublisher.
    """
    def __init__(self, sandbox_mode: bool = True):
        super().__init__(platform_name="linkedin", sandbox_mode=sandbox_mode)
        self.publisher = LinkedInSocialPublisher(sandbox_mode=sandbox_mode)

    def validate_payload(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        body = payload.get("body", "")
        try:
            self.publisher.validate_content(body)
            return True, ""
        except ValueError as err:
            return False, str(err)

    def publish(self, payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        is_valid, error = self.validate_payload(payload)
        if not is_valid:
            raise ValueError(f"LinkedIn validation error: {error}")

        res = self.publisher.publish(content=payload.get("body", ""))
        return self.generate_receipt(
            external_id=res.platform_post_id,
            permalink=res.permalink_url or f"https://www.linkedin.com/feed/update/{res.platform_post_id}",
            payload=payload,
            idempotency_key=idempotency_key
        )
