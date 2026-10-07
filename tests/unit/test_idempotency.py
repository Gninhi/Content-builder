from packages.domain.idempotency import compute_payload_hash, compute_idempotency_key


def test_payload_hash_consistency():
    payload_a = {
        "platform": "linkedin",
        "hook": "Un hook accrocheur",
        "body": "Le corps du texte avec de la valeur.",
        "cta": "Partagez votre avis",
        "hashtags": ["#AI", "#Tech"],
        "media_spec": {"type": "carousel"}
    }
    # Same content with different dictionary key order
    payload_b = {
        "media_spec": {"type": "carousel"},
        "cta": "Partagez votre avis",
        "hashtags": ["#Tech", "#AI"],  # sorted internally
        "body": "Le corps du texte avec de la valeur.",
        "hook": "Un hook accrocheur",
        "platform": "linkedin"
    }

    hash_a = compute_payload_hash(payload_a)
    hash_b = compute_payload_hash(payload_b)
    assert hash_a == hash_b
    assert len(hash_a) == 64  # SHA-256


def test_payload_hash_changes_on_modification():
    base_payload = {
        "platform": "linkedin",
        "hook": "Un hook accrocheur",
        "body": "Le corps du texte avec de la valeur.",
        "cta": "Partagez votre avis",
        "hashtags": ["#AI"]
    }
    original_hash = compute_payload_hash(base_payload)

    # Modify body
    modified_payload = dict(base_payload)
    modified_payload["body"] = "Le corps du texte modifié."
    assert compute_payload_hash(modified_payload) != original_hash

    # Modify cta
    modified_payload = dict(base_payload)
    modified_payload["cta"] = "Nouveau CTA"
    assert compute_payload_hash(modified_payload) != original_hash


def test_idempotency_key_generation():
    key1 = compute_idempotency_key(
        workspace_id="ws_123",
        variant_id="var_456",
        platform="linkedin",
        scheduled_at="2026-10-05T09:00:00Z",
        version=1
    )
    key2 = compute_idempotency_key(
        workspace_id="ws_123",
        variant_id="var_456",
        platform="linkedin",
        scheduled_at="2026-10-05T09:00:00Z",
        version=1
    )
    key_diff_version = compute_idempotency_key(
        workspace_id="ws_123",
        variant_id="var_456",
        platform="linkedin",
        scheduled_at="2026-10-05T09:00:00Z",
        version=2
    )
    assert key1 == key2
    assert key1 != key_diff_version
    assert len(key1) == 64
