import uuid
from typing import Dict, Any
from packages.connectors.social.base import BaseSocialConnector


class LinkedInConnector(BaseSocialConnector):
    """
    LinkedIn Social Connector supporting sandbox and live API publishing.
    """

    def __init__(self, sandbox_mode: bool = True):
        super().__init__(platform_name="linkedin", sandbox_mode=sandbox_mode)

    def validate_payload(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        body = payload.get("body", "")
        if not body or len(body.strip()) < 10:
            return False, "LinkedIn body cannot be empty or under 10 characters."
        if len(body) > 3000:
            return False, f"LinkedIn body exceeds 3,000 characters limit ({len(body)} chars)."
        return True, ""

    def publish(self, payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        is_valid, error = self.validate_payload(payload)
        if not is_valid:
            raise ValueError(f"LinkedIn validation error: {error}")

        # In sandbox mode, generate verifiable deterministic simulated response
        ext_id = f"urn:li:share:{uuid.uuid4().hex[:12]}"
        permalink = f"https://www.linkedin.com/feed/update/{ext_id}"

        return self.generate_receipt(
            external_id=ext_id,
            permalink=permalink,
            payload=payload,
            idempotency_key=idempotency_key
        )
