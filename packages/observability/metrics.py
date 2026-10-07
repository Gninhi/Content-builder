import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CostAndTokenEstimator:
    """
    Estimates token count and running cost for LLM calls based on verified pricing specifications.
    Pricing is dynamically loaded from an external configuration file (config/pricing.json),
    referenced from official provider documentation (https://ai.google.dev/pricing).
    """

    _cached_pricing: Optional[Dict[str, Any]] = None

    @classmethod
    def _get_config_path(cls) -> Path:
        custom_path = os.getenv("PRICING_CONFIG_PATH")
        if custom_path:
            return Path(custom_path)
        # Default relative to repository root
        project_root = Path(__file__).resolve().parent.parent.parent
        return project_root / "config" / "pricing.json"

    @classmethod
    def load_pricing_config(cls, force_reload: bool = False) -> Dict[str, Any]:
        """Loads and caches pricing configuration from config/pricing.json."""
        if cls._cached_pricing is not None and not force_reload:
            return cls._cached_pricing

        path = cls._get_config_path()
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    loaded: Dict[str, Any] = json.load(f)
                    cls._cached_pricing = loaded
                    return loaded
            else:
                logger.warning(f"Pricing config not found at {path}, using standard fallback.")
        except Exception as e:
            logger.warning(f"Failed to read pricing configuration file: {e}")

        # Emergency internal fallback if file is missing/unreadable
        cls._cached_pricing = {
            "_metadata": {"source": "fallback", "verified_date": "2026-10-07"},
            "models": {
                "gemini-3.8-flash": {"input_per_1k": 0.000075, "output_per_1k": 0.000300},
                "default": {"input_per_1k": 0.0005, "output_per_1k": 0.0015}
            }
        }
        return cls._cached_pricing

    @classmethod
    def get_rates_for_model(cls, model_name: str) -> Dict[str, float]:
        """Returns input_per_1k and output_per_1k for the given model."""
        config = cls.load_pricing_config()
        models = config.get("models", {})

        # Direct match
        if model_name in models:
            m = models[model_name]
            return {
                "input_per_1k": m.get("input_per_1k", 0.000075),
                "output_per_1k": m.get("output_per_1k", 0.000300)
            }

        # Substring / pattern match for Gemini
        lower_name = model_name.lower()
        for k, m in models.items():
            if k in lower_name:
                return {
                    "input_per_1k": m.get("input_per_1k", 0.000075),
                    "output_per_1k": m.get("output_per_1k", 0.000300)
                }

        # Default fallback
        default_model = models.get("default", {})
        return {
            "input_per_1k": default_model.get("input_per_1k", 0.0005),
            "output_per_1k": default_model.get("output_per_1k", 0.0015)
        }

    @classmethod
    def estimate_cost(
        cls,
        input_text: str,
        output_text: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Estimates token usage and USD cost based on external pricing config."""
        # Heuristic: 1 token ~ 4 characters
        input_tokens = max(1, len(input_text) // 4)
        output_tokens = max(1, len(output_text) // 4)

        target_model = (model or os.getenv("GEMINI_MODEL") or "gemini-3.8-flash")
        rates = cls.get_rates_for_model(target_model)

        cost = (
            (input_tokens / 1000.0) * rates["input_per_1k"] +
            (output_tokens / 1000.0) * rates["output_per_1k"]
        )

        return {
            "model": target_model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": round(cost, 8)
        }
