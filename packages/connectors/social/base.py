from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime, timezone
import uuid


class BaseSocialConnector(ABC):
    """
    Abstract base class for all social platform connectors.
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
