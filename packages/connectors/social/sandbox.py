import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from packages.connectors.social.base import (
    BaseSocialPublisher,
    SocialPublisherRegistry,
)
from packages.connectors.social.models import (
    PublicationResult,
    PublicationStatus,
    SocialProvider
)


class SandboxSocialPublisher(BaseSocialPublisher):
    """
    Sandbox implementation of SocialPublisher for local testing and CI/CD pipelines.
    Simulates posting, scheduling, deletions, and status checks without contacting external APIs.
    """

    def __init__(
        self,
        provider: SocialProvider = SocialProvider.LINKEDIN,
        sandbox_mode: Optional[bool] = None,
        **kwargs: Any
    ):
        super().__init__(sandbox_mode=True)
        self._provider = provider
        # Simulated platform state: post_id -> post_dict
        self._registry: Dict[str, Dict[str, Any]] = {}

    @property
    def provider(self) -> SocialProvider:
        return self._provider

    def publish(
        self,
        content: str,
        media_urls: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> PublicationResult:
        post_id = f"sandbox_{self._provider.value}_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        post_data = {
            "id": post_id,
            "provider": self._provider,
            "content": content,
            "media_urls": media_urls or [],
            "options": options or {},
            "status": PublicationStatus.PUBLISHED,
            "published_at": now
        }
        self._registry[post_id] = post_data

        return PublicationResult(
            platform_post_id=post_id,
            provider=self._provider,
            status=PublicationStatus.PUBLISHED,
            published_at=now,
            permalink_url=f"https://sandbox.{self._provider.value}.com/posts/{post_id}",
            metadata={"sandbox": True, "media_count": len(media_urls or [])}
        )

    def schedule(
        self,
        content: str,
        scheduled_at: datetime,
        media_urls: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> PublicationResult:
        post_id = f"sandbox_{self._provider.value}_{uuid.uuid4().hex[:12]}"

        post_data = {
            "id": post_id,
            "provider": self._provider,
            "content": content,
            "media_urls": media_urls or [],
            "options": options or {},
            "status": PublicationStatus.SCHEDULED,
            "scheduled_at": scheduled_at
        }
        self._registry[post_id] = post_data

        return PublicationResult(
            platform_post_id=post_id,
            provider=self._provider,
            status=PublicationStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            permalink_url=f"https://sandbox.{self._provider.value}.com/scheduled/{post_id}",
            metadata={"sandbox": True, "scheduled": True}
        )

    def delete(self, platform_post_id: str) -> bool:
        if platform_post_id in self._registry:
            self._registry[platform_post_id]["status"] = PublicationStatus.DELETED
            return True
        return False

    def get_status(self, platform_post_id: str) -> PublicationStatus:
        if platform_post_id not in self._registry:
            return PublicationStatus.FAILED
        return self._registry[platform_post_id]["status"]


SocialPublisherRegistry.register("sandbox", SandboxSocialPublisher)
