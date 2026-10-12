import os
import time
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
import httpx

from packages.connectors.social.base import (
    BaseSocialConnector,
    BaseSocialPublisher,
    SocialPublisherRegistry,
)
from packages.connectors.social.models import (
    PublicationResult,
    PublicationStatus,
    SocialProvider,
)
from packages.connectors.social.exceptions import (
    SocialAuthenticationError,
    SocialPermissionError,
    SocialRateLimitError,
    SocialBillingError,
    SocialDuplicateError,
    SocialNetworkError,
    SocialPublishUnknownError,
    TokenRefreshError,
)


class XSocialPublisher(BaseSocialPublisher):
    """
    Production-ready X (Twitter) API v2 Social Publisher.
    
    Standards & Specifications (verified 2026-10-07 against official X Developer Docs):
    - OAuth 2.0 PKCE (S256): Scopes 'tweet.read tweet.write users.read offline.access'
    - Token lifecycle: Access token ~2h. Automatic refresh with atomic refresh_token rotation.
    - Publication endpoint: POST https://api.x.com/2/tweets
    - Character limit: Strict 280 characters enforcement with URL length weighting.
    - Rate & Cost Guardrails: Respects 'x-rate-limit-reset', monthly budget caps, fail-closed on 402/403 billing.
    - Idempotency & network safety: Raises SocialPublishUnknownError on timeouts to prevent duplicate tweets.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        max_text_length: int = 280,
        monthly_limit: int = 60,
        current_month_publications: int = 0,
        on_token_refreshed: Optional[Callable[[str, str, datetime], None]] = None,
        sandbox_mode: Optional[bool] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        super().__init__(sandbox_mode=sandbox_mode)
        self.access_token = access_token or os.getenv("X_ACCESS_TOKEN")
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
        self.client_id = client_id or os.getenv("X_CLIENT_ID") or os.getenv("X_API_KEY")
        self.client_secret = client_secret or os.getenv("X_CLIENT_SECRET") or os.getenv("X_API_SECRET")
        self.max_text_length = max_text_length
        self.monthly_limit = monthly_limit
        self.current_month_publications = current_month_publications
        self.on_token_refreshed = on_token_refreshed
        self._refresh_lock = threading.Lock()
        self._client = http_client or httpx.Client(timeout=15.0)

    @property
    def provider(self) -> SocialProvider:
        return SocialProvider.X

    @property
    def sandbox_mode(self) -> bool:
        return self._sandbox_mode

    @staticmethod
    def compute_weighted_length(content: str) -> int:
        """
        Computes effective character length according to X (Twitter) API v2 rules:
        Every URL (http:// or https://) is automatically transformed to a t.co link
        and counts as exactly 23 characters, regardless of its raw character count.
        """
        import re
        urls = re.findall(r"https?://\S+", content)
        effective_len = len(content)
        for u in urls:
            # Replace length of actual URL string with standard 23 chars
            effective_len = effective_len - len(u) + 23
        return effective_len

    def validate_content(self, content: str) -> None:
        """Validates body constraints for X posts (5 to max_text_length chars with t.co weighting)."""
        body = content.strip()
        if len(body) < 5:
            raise ValueError("X post content cannot be empty or under 5 characters.")
        weighted_len = self.compute_weighted_length(body)
        if weighted_len > self.max_text_length:
            raise ValueError(
                f"X post content exceeds {self.max_text_length} characters limit "
                f"({weighted_len} weighted chars, {len(body)} raw chars)."
            )

    def ensure_valid_token(self) -> None:
        """
        Validates token freshness and performs atomic refresh if expired or expiring within 60s.
        Uses a thread lock to prevent concurrent refresh token collisions.
        """
        if self.sandbox_mode:
            return

        if not self.access_token:
            raise SocialAuthenticationError("Missing X OAuth access token.", provider=self.provider.value)

        now = datetime.now(timezone.utc)
        needs_refresh = False
        if self.token_expires_at:
            expires_at = self.token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now + timedelta(seconds=60) >= expires_at:
                needs_refresh = True

        if needs_refresh:
            self.refresh_access_token()

    def refresh_access_token(self) -> None:
        """
        Refreshes access token via POST https://api.x.com/2/oauth2/token using refresh_token.
        Atomically updates the rotated refresh_token.
        """
        if not self.refresh_token:
            raise SocialAuthenticationError(
                "X OAuth access token expired and no refresh_token is configured. Reconnection required.",
                provider=self.provider.value
            )

        with self._refresh_lock:
            # Re-check under lock
            now = datetime.now(timezone.utc)
            if self.token_expires_at and self.token_expires_at.tzinfo is None:
                self.token_expires_at = self.token_expires_at.replace(tzinfo=timezone.utc)
            if self.token_expires_at and (now + timedelta(seconds=60) < self.token_expires_at):
                return

            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id or "",
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            try:
                if self.client_id and self.client_secret:
                    resp = self._client.post(
                        "https://api.x.com/2/oauth2/token",
                        data=data,
                        headers=headers,
                        auth=(self.client_id, self.client_secret)
                    )
                else:
                    resp = self._client.post(
                        "https://api.x.com/2/oauth2/token",
                        data=data,
                        headers=headers
                    )
            except Exception as exc:
                raise TokenRefreshError(f"Network error refreshing X token: {exc}", provider=self.provider.value)

            if resp.status_code == 200:
                payload = resp.json()
                new_access_token = payload.get("access_token")
                new_refresh_token = payload.get("refresh_token") or self.refresh_token
                expires_in = payload.get("expires_in", 7200)

                if not new_access_token:
                    raise TokenRefreshError("X token refresh response missing access_token.", provider=self.provider.value)

                new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

                self.access_token = new_access_token
                self.refresh_token = new_refresh_token
                self.token_expires_at = new_expires_at

                if self.on_token_refreshed:
                    self.on_token_refreshed(new_access_token, new_refresh_token, new_expires_at)
            elif resp.status_code in (400, 401):
                raise SocialAuthenticationError(
                    f"X refresh token rejected or revoked (HTTP {resp.status_code}): {resp.text}. Reconnection required.",
                    provider=self.provider.value
                )
            else:
                raise TokenRefreshError(
                    f"X token refresh failed with HTTP {resp.status_code}: {resp.text}",
                    provider=self.provider.value
                )

    @classmethod
    def estimate_post_cost_usd(cls, content: str, media_urls: Optional[List[str]] = None) -> float:
        """
        Estimates publishing cost in USD based on official X API tiers (REQ-20 / FND-06):
        - Base text post: $0.001 nominal estimated API cost
        - URL card processing: $0.0005
        - Media asset processing: $0.005 per uploaded visual/video
        """
        base_cost = 0.001
        has_url = "http://" in content or "https://" in content
        url_cost = 0.0005 if has_url else 0.0
        media_count = len(media_urls) if media_urls else 0
        media_cost = media_count * 0.005
        return round(base_cost + url_cost + media_cost, 4)

    def check_cost_guardrails(self) -> None:
        """Enforces monthly publishing ceiling to prevent runaway API billing."""
        if self.current_month_publications >= self.monthly_limit:
            raise SocialBillingError(
                f"Monthly publication ceiling reached for X ({self.current_month_publications}/{self.monthly_limit}). "
                "Publication blocked by cost guardrails.",
                provider=self.provider.value
            )

    def publish(
        self,
        content: str,
        media_urls: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> PublicationResult:
        self.validate_content(content)
        self.check_cost_guardrails()

        # 1. Sandbox simulation
        if self.sandbox_mode:
            simulated_id = f"{uuid.uuid4().int % 1000000000000000000}"
            self.current_month_publications += 1
            self._sandbox_registry[simulated_id] = PublicationStatus.PUBLISHED
            return PublicationResult(
                platform_post_id=simulated_id,
                provider=self.provider,
                status=PublicationStatus.PUBLISHED,
                published_at=datetime.now(timezone.utc),
                permalink_url=f"https://x.com/user/status/{simulated_id}",
                metadata={"sandbox": True, "monthly_count": self.current_month_publications}
            )

        # 2. Live publication
        self.ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {"text": content}

        try:
            resp = self._client.post(
                "https://api.x.com/2/tweets",
                headers=headers,
                json=payload
            )
        except httpx.TimeoutException as exc:
            # At-most-once safety: request was sent over wire, response timeout
            raise SocialPublishUnknownError(
                f"X publishing timed out: {exc}. Status is unknown; reconciliation required.",
                provider=self.provider.value
            )
        except httpx.RequestError as exc:
            raise SocialNetworkError(f"Network error contacting X: {exc}", provider=self.provider.value)

        if resp.status_code in (200, 201):
            data = resp.json().get("data", {})
            tweet_id = str(data.get("id"))
            self.current_month_publications += 1
            return PublicationResult(
                platform_post_id=tweet_id,
                provider=self.provider,
                status=PublicationStatus.PUBLISHED,
                published_at=datetime.now(timezone.utc),
                permalink_url=f"https://x.com/user/status/{tweet_id}",
                metadata={"response": data, "monthly_count": self.current_month_publications}
            )
        elif resp.status_code == 401:
            raise SocialAuthenticationError(f"X authentication failed (401): {resp.text}", provider=self.provider.value)
        elif resp.status_code in (402, 403):
            err_text = resp.text.lower()
            if "duplicate" in err_text:
                raise SocialDuplicateError(f"X rejected post as duplicate: {resp.text}", provider=self.provider.value)
            if "credit" in err_text or "billing" in err_text or resp.status_code == 402:
                raise SocialBillingError(f"X API billing or tier error: {resp.text}", provider=self.provider.value)
            raise SocialPermissionError(f"X permission or access denied (403): {resp.text}", provider=self.provider.value)
        elif resp.status_code == 429:
            reset_header = resp.headers.get("x-rate-limit-reset")
            retry_sec = None
            if reset_header and reset_header.isdigit():
                reset_epoch = int(reset_header)
                retry_sec = max(0, reset_epoch - int(time.time()))
            raise SocialRateLimitError(
                f"X rate limit exceeded (429): {resp.text}",
                provider=self.provider.value,
                retry_after=retry_sec
            )
        elif resp.status_code >= 500:
            raise SocialNetworkError(f"X platform error (HTTP {resp.status_code}): {resp.text}", provider=self.provider.value)
        else:
            raise SocialPublishUnknownError(
                f"Unexpected X API response (HTTP {resp.status_code}): {resp.text}",
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
        post_id = f"sched_x_{uuid.uuid4().hex[:10]}"
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

        self.ensure_valid_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            resp = self._client.delete(
                f"https://api.x.com/2/tweets/{platform_post_id}",
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return bool(data.get("deleted", True))
            return resp.status_code == 204
        except Exception:
            return False

    def get_status(self, platform_post_id: str) -> PublicationStatus:
        if self.sandbox_mode:
            return self._sandbox_registry.get(platform_post_id, PublicationStatus.PUBLISHED)

        self.ensure_valid_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            resp = self._client.get(
                f"https://api.x.com/2/tweets/{platform_post_id}?tweet.fields=public_metrics",
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
class XTwitterConnector(BaseSocialConnector):
    """
    Legacy X connector maintained for backward compatibility.
    Internally wraps XSocialPublisher.
    """
    def __init__(self, sandbox_mode: bool = True):
        super().__init__(platform_name="x", sandbox_mode=sandbox_mode)
        self.publisher = XSocialPublisher(sandbox_mode=sandbox_mode)

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
            raise ValueError(f"X validation error: {error}")

        res = self.publisher.publish(content=payload.get("body", ""))
        return self.generate_receipt(
            external_id=res.platform_post_id,
            permalink=res.permalink_url or f"https://x.com/user/status/{res.platform_post_id}",
            payload=payload,
            idempotency_key=idempotency_key
        )


SocialPublisherRegistry.register("x", XSocialPublisher)
SocialPublisherRegistry.register("twitter", XSocialPublisher)
