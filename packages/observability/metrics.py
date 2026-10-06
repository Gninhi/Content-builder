from typing import Dict, Any, Optional
import os


class CostAndTokenEstimator:
    """
    Estimates token count and running cost for LLM calls based on model specifications.
    Default pricing aligned with Gemini 3.8 Flash.
    """

    # Gemini 3.8 Flash baseline pricing ($ per 1,000 tokens)
    GEMINI_FLASH_1K_INPUT = 0.000075   # $0.075 per 1M tokens
    GEMINI_FLASH_1K_OUTPUT = 0.000300  # $0.30 per 1M tokens

    # Fallback / standard baseline
    DEFAULT_1K_INPUT = 0.0005
    DEFAULT_1K_OUTPUT = 0.0015

    @classmethod
    def estimate_cost(
        cls,
        input_text: str,
        output_text: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        # Approximate heuristic: 1 token ~ 4 characters
        input_tokens = max(1, len(input_text) // 4)
        output_tokens = max(1, len(output_text) // 4)

        target_model = (model or os.getenv("GEMINI_MODEL") or "gemini-3.8-flash")
        if "gemini" in target_model.lower():
            rate_in = cls.GEMINI_FLASH_1K_INPUT
            rate_out = cls.GEMINI_FLASH_1K_OUTPUT
        else:
            rate_in = cls.DEFAULT_1K_INPUT
            rate_out = cls.DEFAULT_1K_OUTPUT

        cost = (
            (input_tokens / 1000.0) * rate_in +
            (output_tokens / 1000.0) * rate_out
        )

        return {
            "model": target_model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": round(cost, 8)
        }
