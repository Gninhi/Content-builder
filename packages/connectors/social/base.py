import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from packages.connectors.social.models import (
    PublicationResult,
    PublicationStatus,
    SocialProvider,
)


class BaseSocialConnector(ABC):
    """
    Abstract base class for existing social platform connectors.
    Provides sandbox mode, format validation, and receipt generation.
    """

    def __init__(self, platform_name: str, sandbox_mode: bool = True):
        self.platform_name = platform_name
        self.sandbox_mode = sandbox_mode
        self._receipts: Dict[str, Dict[str, Any]] = {}

    @abstractmethod
    def validate_payload(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        """Validates length, character sets, media requirements."""
        pass

    @abstractmethod
    def publish(self, payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        """
        Publishes the content and returns an audit receipt.
        Must respect idempotency.
        """
        pass

    def generate_receipt(
        self,
        external_id: str,
        permalink: str,
        payload: Dict[str, Any],
        idempotency_key: str
    ) -> Dict[str, Any]:
        if idempotency_key in self._receipts:
            return self._receipts[idempotency_key]

        receipt = {
            "receipt_id": str(uuid.uuid4()),
            "platform": self.platform_name,
            "external_id": external_id,
            "permalink": permalink,
            "idempotency_key": idempotency_key,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "sandbox": self.sandbox_mode,
            "final_payload": payload,
            "status": "SUCCESS"
        }
        self._receipts[idempotency_key] = receipt
        return receipt


class SocialPublisher(ABC):
    """
    Standardized abstract interface for publishing and scheduling across social networks.
    Defines the contract for LinkedIn, X, and Sandbox integrations.
    """

    def __init__(self, sandbox_mode: Optional[bool] = None):
        self._sandbox_mode_override = sandbox_mode

    @property
    @abstractmethod
    def provider(self) -> SocialProvider:
        """Returns the social network provider handled by this publisher."""
        pass

    @abstractmethod
    def publish(
        self,
        content: str,
        media_urls: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> PublicationResult:
        """Publishes content immediately to the social platform."""
        pass

    @abstractmethod
    def schedule(
        self,
        content: str,
        scheduled_at: datetime,
        media_urls: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> PublicationResult:
        """Schedules content for future publication."""
        pass

    @abstractmethod
    def delete(self, platform_post_id: str) -> bool:
        """Deletes a previously published or scheduled post."""
        pass

    @abstractmethod
    def get_status(self, platform_post_id: str) -> PublicationStatus:
        """Retrieves the current status of a post on the platform."""
        pass


class BaseSocialPublisher(SocialPublisher):
    """
    Unified base class for all social publishers implementing common sandbox lifecycle,
    idempotency storage, and environment resolution (DRY & Liskov Substitution).
    """

    def __init__(self, sandbox_mode: Optional[bool] = None):
        self._sandbox_mode = self.resolve_sandbox_mode(sandbox_mode)
        self._sandbox_registry: Dict[str, PublicationStatus] = {}

    @property
    def is_sandbox(self) -> bool:
        return self._sandbox_mode

    @staticmethod
    def resolve_sandbox_mode(explicit_mode: Optional[bool] = None) -> bool:
        """
        Determines whether sandbox mode is active.
        Fails closed (sandbox=True) unless LIVE_PUBLISHING_ENABLED is explicitly 'true'.
        """
        if explicit_mode is not None:
            return explicit_mode
        live_enabled = os.getenv("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"
        global_sandbox = os.getenv("SOCIAL_SANDBOX_MODE", "true").lower() == "true"
        return global_sandbox or not live_enabled

    def _sandbox_publish(
        self,
        content: str,
        media_urls: Optional[List[str]] = None,
        prefix: str = "mock_post",
        permalink_domain: str = "example.com"
    ) -> PublicationResult:
        post_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self._sandbox_registry[post_id] = PublicationStatus.PUBLISHED
        return PublicationResult(
            platform_post_id=post_id,
            provider=self.provider,
            status=PublicationStatus.PUBLISHED,
            published_at=datetime.now(timezone.utc),
            permalink_url=f"https://{permalink_domain}/posts/{post_id}",
            metadata={
                "mock": True,
                "provider": self.provider.value,
                "content_length": len(content),
                "media_count": len(media_urls) if media_urls else 0
            }
        )

    def _sandbox_schedule(
        self,
        content: str,
        scheduled_at: datetime,
        prefix: str = "mock_sched",
        permalink_domain: str = "example.com"
    ) -> PublicationResult:
        post_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self._sandbox_registry[post_id] = PublicationStatus.SCHEDULED
        return PublicationResult(
            platform_post_id=post_id,
            provider=self.provider,
            status=PublicationStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            permalink_url=f"https://{permalink_domain}/scheduled/{post_id}",
            metadata={
                "mock": True,
                "provider": self.provider.value,
                "scheduled_at": scheduled_at.isoformat()
            }
        )

    def _sandbox_delete(self, platform_post_id: str) -> bool:
        if platform_post_id in self._sandbox_registry:
            self._sandbox_registry[platform_post_id] = PublicationStatus.DELETED
        return True

    def _sandbox_get_status(self, platform_post_id: str) -> PublicationStatus:
        return self._sandbox_registry.get(platform_post_id, PublicationStatus.PUBLISHED)


class SocialPublisherRegistry:
    """
    Open/Closed Publisher Registry allowing registration and dynamic retrieval
    of platform publishers without hardcoded branching.
    """

    _registry: Dict[str, Type[SocialPublisher]] = {}

    @classmethod
    def register(cls, platform: str, publisher_cls: Type[SocialPublisher]) -> None:
        cls._registry[platform.lower().strip()] = publisher_cls

    @classmethod
    def get_publisher_class(cls, platform: str) -> Type[SocialPublisher]:
        clean = platform.lower().strip()
        if clean not in cls._registry:
            raise ValueError(
                f"Unsupported platform '{platform}'. Registered platforms: {list(cls._registry.keys())}"
            )
        return cls._registry[clean]

    @classmethod
    def list_supported_platforms(cls) -> List[str]:
        return list(cls._registry.keys())
