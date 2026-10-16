from typing import Any, Dict, List, Optional
import re


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def render_publishable_text(variant: Any) -> str:
    """
    Canonical renderer for publication: converts a content variant into its
    final publishable string representation.
    Used identiquement across:
    1. UI preview rendering
    2. HITL Approval seal calculation
    3. Social network dispatcher & publisher worker
    """
    platform = str(_get_val(variant, "platform", "linkedin")).lower()
    raw_body = str(_get_val(variant, "body", "") or "").strip()
    raw_hook = str(_get_val(variant, "hook", "") or "").strip()
    raw_cta = str(_get_val(variant, "cta", "") or "").strip()
    hashtags = _get_val(variant, "hashtags", []) or []

    parts = []

    # 1. Hook handling
    if raw_hook and not raw_body.startswith(raw_hook):
        parts.append(raw_hook)

    # 2. Body handling
    if raw_body:
        parts.append(raw_body)

    # 3. CTA handling
    if raw_cta and not raw_body.endswith(raw_cta) and raw_cta not in raw_body:
        parts.append(raw_cta)

    # 4. Hashtags handling
    if hashtags and isinstance(hashtags, (list, tuple, set)):
        formatted_tags = []
        for tag in sorted(set(hashtags)):
            cleaned = str(tag).strip()
            if cleaned:
                formatted_tags.append(cleaned if cleaned.startswith("#") else f"#{cleaned}")
        if formatted_tags:
            tags_str = " ".join(formatted_tags)
            if tags_str not in raw_body:
                parts.append(tags_str)

    rendered = "\n\n".join(p for p in parts if p)

    # 5. Platform-specific length constraints (X / Twitter: 280 characters limit)
    if platform in ("x", "twitter"):
        if len(rendered) > 280:
            truncated = rendered[:277].rstrip()
            last_space = max(truncated.rfind(" "), truncated.rfind("\n"))
            if last_space > 200:
                truncated = truncated[:last_space].rstrip()
            rendered = f"{truncated}..."

    return rendered


def extract_publishable_media(variant: Any) -> List[str]:
    """
    Extracts publishable media URLs from a variant specification.
    """
    media_spec = _get_val(variant, "media_spec", {}) or {}
    if not isinstance(media_spec, dict):
        return []

    urls: List[str] = []
    if "urls" in media_spec and isinstance(media_spec["urls"], (list, tuple)):
        urls.extend(str(u) for u in media_spec["urls"] if u)
    elif "media_urls" in media_spec and isinstance(media_spec["media_urls"], (list, tuple)):
        urls.extend(str(u) for u in media_spec["media_urls"] if u)
    elif "url" in media_spec and isinstance(media_spec["url"], str):
        urls.append(media_spec["url"])

    return urls
