import hashlib
import json
from typing import Any, Dict


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """
    Computes a canonical SHA-256 hash of a content variant payload.
    Any modification to body, hook, cta, hashtags, or media specification
    will produce a different hash, invalidating prior human approvals.
    """
    normalized = {
        "platform": payload.get("platform", ""),
        "hook": (payload.get("hook") or "").strip(),
        "body": (payload.get("body") or "").strip(),
        "cta": (payload.get("cta") or "").strip(),
        "hashtags": sorted(payload.get("hashtags") or []),
        "media_spec": payload.get("media_spec") or {},
    }
    serialized = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_idempotency_key(
    workspace_id: str,
    variant_id: str,
    platform: str,
    scheduled_at: str,
    version: int = 1
) -> str:
    """
    Computes the unique publication idempotency key as mandated by PRD Section 5:
    idempotency_key = hash(workspace_id, variant_id, platform, scheduled_at, version)
    """
    raw_key = f"{workspace_id}:{variant_id}:{platform}:{scheduled_at}:{version}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
