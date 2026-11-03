from typing import Any
from packages.observability.pii import PIIRedactor


def mask_pii(data: Any) -> Any:
    """
    Recursively redacts PII, tokens, and secrets from arbitrary data structures.
    Supports str, dict, list, tuple, and nested structures.
    """
    if isinstance(data, str):
        return PIIRedactor.redact(data)
    elif isinstance(data, dict):
        return {k: mask_pii(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_pii(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(mask_pii(item) for item in data)
    return data
