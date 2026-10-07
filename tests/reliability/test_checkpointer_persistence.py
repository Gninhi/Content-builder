import tempfile
from pathlib import Path
from services.orchestration.graphs.approval import create_approval_graph
from services.orchestration.checkpointer import get_checkpointer


def test_human_review_interrupt_survives_process_restart():
    """
    CRITICAL RELIABILITY REQUIREMENT (REL-01):
    Verifies that a LangGraph HITL interrupt before 'human_review'
    persists across process restarts when backed by durable storage (SQLite/PostgreSQL),
    whereas an in-memory checkpointer would drop all pending states.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "persistent_checkpoint.db")

        # --- PROCESS RUN 1: Initial execution until human interruption ---
        cp_1 = get_checkpointer(checkpointer_type="sqlite", conn_string=db_path)
        graph_1 = create_approval_graph(checkpointer=cp_1)

        thread_id = "thread_hitl_test_999"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "variant_id": "var_durable_123",
            "content_payload": {
                "platform": "linkedin",
                "body": "Post en attente de validation éditoriale humaine."
            },
            "payload_hash": "hash_secure_abc",
            "reviewer_id": "reviewer_martial",
            "decision": "pending"
        }

        # Invoke until the interrupt_before=["human_review"] gate
        _ = graph_1.invoke(initial_state, config=config)

        # Confirm process 1 stopped at human_review
        checkpoint_state_1 = graph_1.get_state(config)
        assert "human_review" in checkpoint_state_1.next
        assert checkpoint_state_1.values["variant_id"] == "var_durable_123"

        # Simulate complete process crash / shutdown
        del graph_1
        del cp_1

        # --- PROCESS RUN 2: Re-instantiate from fresh process / memory space ---
        cp_2 = get_checkpointer(checkpointer_type="sqlite", conn_string=db_path)
        graph_2 = create_approval_graph(checkpointer=cp_2)

        # Checkpoint MUST be fully recovered from durable storage
        recovered_state = graph_2.get_state(config)
        assert recovered_state is not None
        assert "human_review" in recovered_state.next
        assert recovered_state.values["variant_id"] == "var_durable_123"
        assert recovered_state.values["payload_hash"] == "hash_secure_abc"

        # Resume execution with human approval decision
        graph_2.update_state(config, {"decision": "approve"})
        _ = graph_2.invoke(None, config=config)

        # Execution should now complete to END
        completed_state = graph_2.get_state(config)
        assert len(completed_state.next) == 0  # Reached END
        assert completed_state.values["decision"] == "approve"
