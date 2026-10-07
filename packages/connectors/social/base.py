import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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
