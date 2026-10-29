import uuid
import logging
from typing import Dict, Any, Optional, List
from langfuse.langchain import CallbackHandler
from packages.security.pii import mask_pii

logger = logging.getLogger(__name__)


class SanitizedLangfuseCallbackHandler(CallbackHandler):
    """
    Subclass of Langfuse CallbackHandler enforcing strict, automated PII, token,
    and secret masking on all prompts, tool inputs/outputs, chain payloads, and metadata
    prior to dispatching telemetry to Langfuse collectors (Finding X-005).
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any
    ):
        super().__init__(public_key=public_key)
        self.session_id = session_id
        self.user_id = user_id
        self.extra_tags = tags or []

    def on_llm_start(
        self,
        serialized: Optional[Dict[str, Any]],
        prompts: List[str],
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Any:
        sanitized_prompts = [mask_pii(p) for p in prompts]
        sanitized_metadata = mask_pii(metadata) if metadata else None
        sanitized_kwargs = mask_pii(kwargs)
        resolved_run_id = run_id or uuid.uuid4()

        if hasattr(self, "_handle_llm_start"):
            self._handle_llm_start(
                serialized=serialized,
                prompts=sanitized_prompts,
                run_id=resolved_run_id,
                parent_run_id=parent_run_id,
                tags=tags,
                metadata=sanitized_metadata,
                **sanitized_kwargs
            )

        try:
            return super().on_llm_start(
                serialized=serialized,
                prompts=sanitized_prompts,
                run_id=resolved_run_id,
                parent_run_id=parent_run_id,
                tags=tags,
                metadata=sanitized_metadata,
                **sanitized_kwargs
            )
        except Exception as e:
            logger.debug(f"Langfuse on_llm_start super call: {e}")

    def on_chain_start(
        self,
        serialized: Optional[Dict[str, Any]],
        inputs: Any,
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Any:
        sanitized_inputs = mask_pii(inputs)
        sanitized_metadata = mask_pii(metadata) if metadata else None
        sanitized_kwargs = mask_pii(kwargs)
        resolved_run_id = run_id or uuid.uuid4()

        if hasattr(self, "_handle_chain_start"):
            self._handle_chain_start(
                serialized=serialized,
                inputs=sanitized_inputs,
                run_id=resolved_run_id,
                parent_run_id=parent_run_id,
                tags=tags,
                metadata=sanitized_metadata,
                **sanitized_kwargs
            )

        try:
            return super().on_chain_start(
                serialized=serialized,
                inputs=sanitized_inputs,
                run_id=resolved_run_id,
                parent_run_id=parent_run_id,
                tags=tags,
                metadata=sanitized_metadata,
                **sanitized_kwargs
            )
        except Exception as e:
            logger.debug(f"Langfuse on_chain_start super call: {e}")

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any
    ) -> Any:
        sanitized_outputs = mask_pii(outputs)
        sanitized_kwargs = mask_pii(kwargs)
        resolved_run_id = run_id or uuid.uuid4()

        if hasattr(self, "_handle_chain_end"):
            self._handle_chain_end(
                outputs=sanitized_outputs,
                run_id=resolved_run_id,
                parent_run_id=parent_run_id,
                **sanitized_kwargs
            )

        try:
            return super().on_chain_end(
                outputs=sanitized_outputs,
                run_id=resolved_run_id,
                parent_run_id=parent_run_id,
                **sanitized_kwargs
            )
        except Exception as e:
            logger.debug(f"Langfuse on_chain_end super call: {e}")

    def on_tool_start(
        self,
        serialized: Optional[Dict[str, Any]],
        input_str: str,
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Any:
        sanitized_input = mask_pii(input_str)
        sanitized_metadata = mask_pii(metadata) if metadata else None
        sanitized_kwargs = mask_pii(kwargs)
        resolved_run_id = run_id or uuid.uuid4()

        try:
            return super().on_tool_start(
                serialized=serialized,
                input_str=sanitized_input,
                run_id=resolved_run_id,
                parent_run_id=parent_run_id,
                tags=tags,
                metadata=sanitized_metadata,
                **sanitized_kwargs
            )
        except Exception as e:
            logger.debug(f"Langfuse on_tool_start super call: {e}")

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: Optional[uuid.UUID] = None,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any
    ) -> Any:
        sanitized_output = mask_pii(output)
        sanitized_kwargs = mask_pii(kwargs)
        resolved_run_id = run_id or uuid.uuid4()

        try:
            return super().on_tool_end(
                output=sanitized_output,
                run_id=resolved_run_id,
                parent_run_id=parent_run_id,
                **sanitized_kwargs
            )
        except Exception as e:
            logger.debug(f"Langfuse on_tool_end super call: {e}")
