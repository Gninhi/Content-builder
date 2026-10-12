import json
from unittest.mock import MagicMock
from pydantic import BaseModel, Field

from services.orchestration.providers.nvidia import NVIDIAProviderAdapter
from services.orchestration.structured_output import (
    make_schema_template,
    extract_json_from_text,
    invoke_structured_output,
)
from packages.observability.metrics import CostAndTokenEstimator


class SampleArticleSchema(BaseModel):
    title: str = Field(description="Article title")
    summary: str = Field(description="Executive summary")
    word_count: int = Field(description="Target length")


def test_nvidia_provider_catalog_and_default_model():
    """Validates that NVIDIAProviderAdapter exposes the active catalog and correct default model."""
    provider = NVIDIAProviderAdapter()
    assert provider.provider_id == "nvidia"
    assert provider.get_default_model_id() in ("z-ai/glm-5.3-flash", "meta/llama-3.2-11b-vision-instruct")

    models = provider.list_models()
    model_ids = [m.model_id for m in models]

    # Verify active models are present and old 410 EOL model is replaced
    assert "meta/llama-3.2-11b-vision-instruct" in model_ids
    assert "nvidia/llama-3.1-nemotron-70b-instruct" in model_ids
    assert "meta/llama-3.2-90b-vision-instruct" in model_ids

    # Verify capabilities
    default_model = next(m for m in models if m.model_id == "meta/llama-3.2-11b-vision-instruct")
    assert default_model.capabilities["structured_output"] is True
    assert default_model.capabilities["text_generation"] is True


def test_nvidia_chat_model_infer_path_routing_override():
    """Verifies that ChatNVIDIA instances have their infer_path correctly configured to /chat/completions."""
    provider = NVIDIAProviderAdapter()
    model = provider.build_chat_model(
        model_id="meta/llama-3.2-11b-vision-instruct",
        temperature=0.2,
        api_key="nvapi-mock-test-key-12345678",
    )
    assert hasattr(model, "_client")
    # Verify the infer_path was explicitly patched to avoid NVIDIA 451 routing defect
    assert model._client.infer_path == "{base_url}/chat/completions"


def test_structured_output_schema_template():
    """Verifies that make_schema_template generates valid dict structure with schema keys."""
    template = make_schema_template(SampleArticleSchema)
    assert "title" in template
    assert "summary" in template
    assert "word_count" in template
    assert isinstance(template["word_count"], int)


def test_extract_json_from_text_variants():
    """Verifies json fence extraction and edge cases."""
    # Fenced markdown with json
    t1 = "Here is the result:\n```json\n{\"title\": \"AI in 2026\", \"summary\": \"Cool stuff\", \"word_count\": 500}\n```\nHope it helps!"
    assert json.loads(extract_json_from_text(t1))["title"] == "AI in 2026"

    # Fenced markdown without json tag
    t2 = "```\n{\"title\": \"No Tag\", \"summary\": \"Valid\", \"word_count\": 200}\n```"
    assert json.loads(extract_json_from_text(t2))["title"] == "No Tag"

    # Raw string with surrounding text
    t3 = "Preamble {\"title\": \"Raw\", \"summary\": \"Direct\", \"word_count\": 100} Postamble"
    assert json.loads(extract_json_from_text(t3))["title"] == "Raw"


def test_invoke_structured_output_clean_first_attempt():
    """Verifies invoke_structured_output directly parsing valid output."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "title": "Quantum Computing",
        "summary": "Major breakthroughs in error correction.",
        "word_count": 850
    })
    mock_llm.invoke.return_value = mock_response

    result = invoke_structured_output(mock_llm, SampleArticleSchema, "Write an article overview")
    assert isinstance(result, SampleArticleSchema)
    assert result.title == "Quantum Computing"
    assert result.word_count == 850
    assert mock_llm.invoke.call_count == 1


def test_invoke_structured_output_multiline_newlines():
    """Verifies RFC 8259 strict=False handles literal multiline strings."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    # Literal newlines inside JSON string value
    mock_response.content = '{\n  "title": "Line1\\nLine2",\n  "summary": "Paragraph 1\n\nParagraph 2",\n  "word_count": 300\n}'
    mock_llm.invoke.return_value = mock_response

    result = invoke_structured_output(mock_llm, SampleArticleSchema, "Prompt")
    assert isinstance(result, SampleArticleSchema)
    assert "Paragraph 1" in result.summary


def test_invoke_structured_output_repair_step_success():
    """Verifies that 1 repair step is executed on syntax/validation failure and succeeds."""
    mock_llm = MagicMock()
    # First response is malformed
    bad_response = MagicMock()
    bad_response.content = "I cannot provide json directly, but the title is Quantum and word count is invalid"

    # Second response (repair) is valid
    repaired_response = MagicMock()
    repaired_response.content = json.dumps({
        "title": "Repaired Article",
        "summary": "Repaired summary",
        "word_count": 400
    })

    mock_llm.invoke.side_effect = [bad_response, repaired_response]

    result = invoke_structured_output(mock_llm, SampleArticleSchema, "Prompt requiring repair")
    assert isinstance(result, SampleArticleSchema)
    assert result.title == "Repaired Article"
    assert mock_llm.invoke.call_count == 2


def test_invoke_structured_output_fails_after_repair_exhausted():
    """Verifies failure safely returns None if repair fails to produce valid schema."""
    mock_llm = MagicMock()
    bad_response = MagicMock()
    bad_response.content = "Completely invalid non-json text"
    mock_llm.invoke.return_value = bad_response

    result = invoke_structured_output(mock_llm, SampleArticleSchema, "Prompt")
    assert result is None


def test_pricing_config_nvidia_models_calculation():
    """Verifies NVIDIA model pricing entries and cost calculation."""
    CostAndTokenEstimator.load_pricing_config(force_reload=True)

    res = CostAndTokenEstimator.estimate_cost(
        "A" * 4000,
        "B" * 4000,
        model="meta/llama-3.2-11b-vision-instruct"
    )
    assert res["model"] == "meta/llama-3.2-11b-vision-instruct"
    assert res["input_tokens"] == 1000
    assert res["output_tokens"] == 1000
    assert round(res["estimated_cost_usd"], 6) == 0.00015
