import pytest
from langgraph.checkpoint.memory import MemorySaver
from services.orchestration.checkpointer import TenantGuardedCheckpointer, get_checkpointer


def test_tenant_guarded_checkpointer_blocks_cross_tenant_access():
    """ARC-02: Verifies that TenantGuardedCheckpointer strictly prevents cross-tenant thread access."""
    inner = MemorySaver()
    guarded = TenantGuardedCheckpointer(inner)

    # Workspace A writes state to its thread
    config_a = {"configurable": {"thread_id": "ws_alpha:thread_123", "workspace_id": "ws_alpha"}}
    checkpoint = {
        "v": 1,
        "id": "cp_1",
        "ts": "2026-11-02T12:00:00Z",
        "channel_values": {},
        "channel_versions": {},
        "versions_seen": {},
    }
    metadata = {
        "step": 1,
        "summary": "Alpha confidential research",
        "access_token": "secret_oauth_token_alpha",
    }
    res_cfg = guarded.put(config_a, checkpoint, metadata=metadata, new_versions={})

    # Workspace A reads its own state: Allowed
    state_a = guarded.get_tuple(res_cfg)
    assert state_a is not None
    assert state_a.metadata["summary"] == "Alpha confidential research"
    # Verification that token was redacted before persisting
    assert state_a.metadata["access_token"] == "[REDACTED_FROM_CHECKPOINT]"

    # Attacker in Workspace B tries to read Workspace A's thread: Strictly Blocked
    config_b_attacking_a = {"configurable": {"thread_id": "ws_alpha:thread_123", "workspace_id": "ws_beta"}}
    with pytest.raises(PermissionError) as exc_info:
        guarded.get_tuple(config_b_attacking_a)
    assert "Cross-tenant checkpoint read denied" in str(exc_info.value)

    # Attacker in Workspace B tries to write to Workspace A's thread: Strictly Blocked
    with pytest.raises(PermissionError) as exc_write_info:
        guarded.put(config_b_attacking_a, checkpoint, metadata={"step": 2}, new_versions={})
    assert "Cross-tenant checkpoint write denied" in str(exc_write_info.value)


def test_get_checkpointer_factory_wraps_with_tenant_guard():
    """Verifies that get_checkpointer returns a TenantGuardedCheckpointer by default."""
    cp = get_checkpointer(checkpointer_type="memory")
    assert isinstance(cp, TenantGuardedCheckpointer)
