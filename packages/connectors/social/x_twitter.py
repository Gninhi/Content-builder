import uuid
from typing import Dict, Any
from packages.connectors.social.base import BaseSocialConnector


class XTwitterConnector(BaseSocialConnector):
    """
    X (Twitter) Connector with 280 character limit enforcement and thread support.
    """

    def __init__(self, sandbox_mode: bool = True):
        super().__init__(platform_name="x", sandbox_mode=sandbox_mode)

    def validate_payload(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        body = payload.get("body", "")
        if not body or len(body.strip()) < 5:
            return False, "X post body cannot be empty or under 5 characters."
        
        # Check if single tweet or thread
        is_thread = payload.get("media_spec", {}).get("is_thread", False)
        if not is_thread and len(body) > 280:
            return False, f"X single tweet exceeds 280 characters ({len(body)} chars). Consider formatting as a thread."
        return True, ""

    def publish(self, payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        is_valid, error = self.validate_payload(payload)
        if not is_valid:
            raise ValueError(f"X validation error: {error}")

        tweet_id = f"{uuid.uuid4().int % 1000000000000000000}"
        permalink = f"https://x.com/user/status/{tweet_id}"

        return self.generate_receipt(
            external_id=tweet_id,
            permalink=permalink,
            payload=payload,
            idempotency_key=idempotency_key
        )
