import json
from pathlib import Path
from packages.observability.metrics import CostAndTokenEstimator


def test_pricing_config_file_exists_and_valid():
    """Verifies that config/pricing.json exists and conforms to standard schema."""
    config_path = Path("config/pricing.json")
    assert config_path.exists(), "config/pricing.json must exist"

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "_metadata" in data
    assert "source" in data["_metadata"]
    assert "ai.google.dev/pricing" in data["_metadata"]["source"]
    assert "verified_date" in data["_metadata"]
    assert "models" in data
    assert "gemini-3.8-flash" in data["models"]

    flash = data["models"]["gemini-3.8-flash"]
    assert flash["input_per_1m"] == 0.75
    assert flash["output_per_1m"] == 3.75
    assert flash["input_per_1k"] == 0.00075
    assert flash["output_per_1k"] == 0.00375


def test_cost_estimator_uses_external_pricing():
    """Verifies that CostAndTokenEstimator loads pricing from config and computes correctly."""
    CostAndTokenEstimator.load_pricing_config(force_reload=True)

    sample_in = "A" * 4000   # ~1000 tokens
    sample_out = "B" * 4000  # ~1000 tokens

    res = CostAndTokenEstimator.estimate_cost(sample_in, sample_out, model="gemini-3.8-flash")
    assert res["model"] == "gemini-3.8-flash"
    assert res["input_tokens"] == 1000
    assert res["output_tokens"] == 1000
    # Expected: 1.0 * 0.00075 + 1.0 * 0.00375 = 0.004500
    assert round(res["estimated_cost_usd"], 6) == 0.0045


def test_cost_estimator_custom_model_and_fallback():
    """Verifies custom model rates or fallback handling."""
    res_pro = CostAndTokenEstimator.estimate_cost("A" * 4000, "B" * 4000, model="gemini-1.5-pro")
    # Expected: 1.0 * 0.00125 + 1.0 * 0.00500 = 0.00625
    assert round(res_pro["estimated_cost_usd"], 5) == 0.00625

    res_unknown = CostAndTokenEstimator.estimate_cost("A" * 4000, "B" * 4000, model="unknown-llm")
    # Default rates: 0.0005 + 0.0015 = 0.002
    assert round(res_unknown["estimated_cost_usd"], 4) == 0.002
