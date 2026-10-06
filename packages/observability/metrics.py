from typing import Dict, Any


class CostAndTokenEstimator:
    """
    Estimates token count and running cost for LLM calls.
    """

    # Baseline cost estimates per 1,000 tokens
    COST_PER_1K_INPUT = 0.0005
    COST_PER_1K_OUTPUT = 0.0015

    @classmethod
    def estimate_cost(cls, input_text: str, output_text: str) -> Dict[str, Any]:
        # Approximate: 1 token ~ 4 characters
        input_tokens = max(1, len(input_text) // 4)
        output_tokens = max(1, len(output_text) // 4)

        cost = (
            (input_tokens / 1000.0) * cls.COST_PER_1K_INPUT +
            (output_tokens / 1000.0) * cls.COST_PER_1K_OUTPUT
        )

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": round(cost, 6)
        }
