import pytest
from pydantic import BaseModel, Field
from typing import List

from services.orchestration.structured_output import (
    extract_json_from_text,
    record_structured_output_metric,
    get_structured_output_validity_rates,
    make_schema_template
)
from services.orchestration.providers.nvidia import strip_reasoning_tokens


class SampleIdeaOutput(BaseModel):
    title: str = Field(description="Titre de l'idée")
    score: float = Field(description="Score de 0 à 100")
    tags: List[str] = Field(description="Mots-clés")


def test_t14_structured_output_reasoning_stripping_and_schema_validation():
    """
    T14 AUDIT TEST: Mesure de la validité des sorties structurées Pydantic
    sur GLM-5.3 (stripping de <think>, détection de blocs markdown, réparation).
    """
    # 1. Élimination des tokens de raisonnement <think>...</think> (GLM-5.3 CoT)
    raw_glm_response = """
    <think>
    Nous analysons la directive EU AI Act de 2026.
    L'angle doit porter sur la conformité des systèmes agentiques.
    Calculons le score de pertinence : 95.0.
    </think>
    ```json
    {
      "title": "Audit de conformité EU AI Act pour architectures agentiques",
      "score": 95.0,
      "tags": ["ia", "conformite", "rgpd"]
    }
    ```
    """

    cleaned_cot = strip_reasoning_tokens(raw_glm_response)
    assert "<think>" not in cleaned_cot
    assert "</think>" not in cleaned_cot
    assert "Calculons le score" not in cleaned_cot

    # 2. Extraction du JSON pur et validation Pydantic
    json_str = extract_json_from_text(raw_glm_response)
    parsed = SampleIdeaOutput.model_validate_json(json_str)

    assert parsed.title == "Audit de conformité EU AI Act pour architectures agentiques"
    assert parsed.score == 95.0
    assert len(parsed.tags) == 3

    # 3. Métrique de taux de validité (REQ-23 / seuil attendu >= 99%)
    record_structured_output_metric("ideation_agent", valid=True, repaired=False)
    record_structured_output_metric("ideation_agent", valid=True, repaired=True)
    record_structured_output_metric("ideation_agent", valid=True, repaired=False)
    rates = get_structured_output_validity_rates()
    assert rates["ideation_agent"] == 100.0

    # 4. Génération de gabarit de schéma pour le guidage prompt
    template = make_schema_template(SampleIdeaOutput)
    assert "title" in template
    assert "score" in template
    assert isinstance(template["tags"], list)
