import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def make_schema_template(model_cls: Type[BaseModel]) -> Dict[str, Any]:
    """
    Recursively builds an intuitive JSON template instance with dummy/descriptive values
    from a Pydantic model class. LLMs follow this concrete format far more reliably
    than raw JSON schema specifications.
    """
    schema = model_cls.model_json_schema()
    defs = schema.get("$defs", {})

    def resolve_prop(prop: Dict[str, Any]) -> Any:
        if "$ref" in prop:
            ref_name = prop["$ref"].split("/")[-1]
            ref_schema = defs.get(ref_name, {})
            return resolve_object(ref_schema)
        
        p_type = prop.get("type")
        if p_type == "string":
            desc = prop.get("description")
            return desc if desc else "texte"
        elif p_type == "integer":
            return 1
        elif p_type == "number":
            return 0.95
        elif p_type == "boolean":
            return True
        elif p_type == "array":
            items = prop.get("items", {})
            return [resolve_prop(items)]
        elif p_type == "object":
            return resolve_object(prop)
        return ""

    def resolve_object(obj_schema: Dict[str, Any]) -> Dict[str, Any]:
        res = {}
        props = obj_schema.get("properties", {})
        for k, v in props.items():
            res[k] = resolve_prop(v)
        return res

    return resolve_object(schema)


_STRUCTURED_OUTPUT_METRICS: Dict[str, Dict[str, int]] = {}


def record_structured_output_metric(agent_name: str, valid: bool, repaired: bool = False) -> None:
    """Records validation success/failure for an agent to track validity rate."""
    if agent_name not in _STRUCTURED_OUTPUT_METRICS:
        _STRUCTURED_OUTPUT_METRICS[agent_name] = {"total": 0, "valid": 0, "repaired": 0}
    _STRUCTURED_OUTPUT_METRICS[agent_name]["total"] += 1
    if valid:
        _STRUCTURED_OUTPUT_METRICS[agent_name]["valid"] += 1
    if repaired:
        _STRUCTURED_OUTPUT_METRICS[agent_name]["repaired"] += 1


def get_structured_output_validity_rates() -> Dict[str, float]:
    """Returns validity percentage per agent."""
    res = {}
    for agent, stats in _STRUCTURED_OUTPUT_METRICS.items():
        total = stats.get("total", 0)
        res[agent] = round(stats.get("valid", 0) / max(1, total) * 100.0, 2)
    return res


def repair_json_brackets(text: str) -> str:
    """Attempts to close truncated JSON strings, objects, or arrays."""
    if not text:
        return text
    in_string = False
    escape = False
    stack = []
    for char in text:
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char in ('{', '['):
                stack.append(char)
            elif char == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif char == ']' and stack and stack[-1] == '[':
                stack.pop()

    repaired = text
    if in_string:
        repaired += '"'
    while stack:
        opener = stack.pop()
        repaired += '}' if opener == '{' else ']'
    return repaired


def extract_json_from_text(text: str) -> str:
    """
    Extracts valid JSON string from raw LLM output.
    Strips reasoning tokens (<think>...</think>), markdown code fences,
    and isolates the outermost JSON object or array.
    """
    if not text:
        return ""
    # Strip chain-of-thought tokens from reasoning models (e.g. GLM-5.3)
    t = re.sub(r"<think>.*?(?:</think>|$)", "", text, flags=re.DOTALL).strip()
    fence = chr(96) * 3
    if fence + "json" in t:
        parts = t.split(fence + "json")
        if len(parts) > 1:
            t = parts[1].split(fence)[0]
    elif fence in t:
        parts = t.split(fence)
        if len(parts) > 1:
            t = parts[1].split(fence)[0]
    
    t = t.strip()
    
    # Locate first { and last }
    first_brace = t.find("{")
    last_brace = t.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return t[first_brace:last_brace + 1]
    elif first_brace != -1:
        return t[first_brace:]
    
    # Check for array [ ... ]
    first_bracket = t.find("[")
    last_bracket = t.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        return t[first_bracket:last_bracket + 1]
    elif first_bracket != -1:
        return t[first_bracket:]
    
    return t


def invoke_structured_output(
    model: Any,
    schema_cls: Type[T],
    prompt: str,
    callbacks: Optional[List[Any]] = None,
    max_repair_retries: int = 1,
    agent_name: str = "default_agent"
) -> Optional[T]:
    """
    Universal, resilient structured output invoker for all LLM providers (NVIDIA GLM, Gemini, etc.).
    Strategy:
    1. Attempts native .with_structured_output(schema_cls) first when available.
    2. If native fails or isn't available, injects an explicit JSON template, strips reasoning tokens,
       parses via non-strict JSON parser to allow multiline strings, and validates via strict Pydantic.
    3. If validation fails, performs exactly 1 automated repair step with targeted error feedback.
    4. Logs and tracks validity rate per agent.
    """
    if model is None:
        return None

    config = {"callbacks": callbacks} if callbacks else {}
    model_name = getattr(model, "model_name", getattr(model, "model", str(type(model).__name__)))

    # 1. Try native structured output first (for Gemini / OpenAI models with tool schema support)
    # NVIDIA GLM reasoning models (e.g. z-ai/glm-5.3-flash) emit thinking tokens and require schema template prompt
    is_nvidia_or_glm = (
        "nvidia" in str(type(model)).lower()
        or "resilient" in str(type(model)).lower()
        or "glm" in getattr(model, "model_id", "").lower()
        or "z-ai" in getattr(model, "model_id", "").lower()
    )
    if not is_nvidia_or_glm and hasattr(model, "with_structured_output"):
        try:
            structured_model = model.with_structured_output(schema_cls)
            result = structured_model.invoke(prompt, config=config)
            if isinstance(result, schema_cls):
                record_structured_output_metric(agent_name, True)
                return result
            if isinstance(result, dict):
                validated = schema_cls.model_validate(result)
                record_structured_output_metric(agent_name, True)
                return validated
        except Exception as e:
            logger.debug(f"Native structured output skipped for {model_name} ({e}), falling back to schema template")

    # 2. Template-based prompt injection for NVIDIA and fallbacks
    template_obj = make_schema_template(schema_cls)
    template_str = json.dumps(template_obj, indent=2, ensure_ascii=False)

    augmented_prompt = f"""{prompt}

CONSIGNE STRICTE DE FORMAT :
Tu dois répondre UNIQUEMENT par un objet JSON valide correspondant très exactement à la structure ci-dessous :
{template_str}

RÈGLES IMPÉRATIVES :
1. Remplis chaque clé avec le contenu pertinent demandé.
2. Renvoie UNIQUEMENT le code JSON brut.
3. N'inclus AUCUN texte explicatif, AUCUNE formule de politesse, AUCUNE balise markdown (pas de ```json ni de ```).
"""

    try:
        response = model.invoke([HumanMessage(content=augmented_prompt)], config=config)
        raw_text = response.content if hasattr(response, "content") else str(response)
        clean_json = extract_json_from_text(raw_text)

        try:
            try:
                data = json.loads(clean_json, strict=False)
            except Exception:
                data = json.loads(repair_json_brackets(clean_json), strict=False)
            validated = schema_cls.model_validate(data)
            record_structured_output_metric(agent_name, True)
            return validated
        except Exception as initial_err:
            logger.warning(
                f"Initial JSON validation failed for {model_name} ({initial_err}). Initiating repair step..."
            )
            if max_repair_retries <= 0:
                record_structured_output_metric(agent_name, False)
                return None

            # 3. Exactly 1 Repair Step
            repair_prompt = f"""La réponse précédente n'a pas pu être validée selon le format attendu.
Erreur de validation constatée : {initial_err}

Contenu précédemment retourné :
{clean_json[:4000]}

Mission de correction :
Corrige l'erreur et renvoie UNIQUEMENT un objet JSON valide conforme à la structure :
{template_str}
Renvoie uniquement le JSON pur, sans balises markdown."""

            repair_resp = model.invoke([HumanMessage(content=repair_prompt)], config=config)
            repair_raw = repair_resp.content if hasattr(repair_resp, "content") else str(repair_resp)
            repair_clean = extract_json_from_text(repair_raw)
            try:
                repair_data = json.loads(repair_clean, strict=False)
            except Exception:
                repair_data = json.loads(repair_json_brackets(repair_clean), strict=False)
            repaired_result = schema_cls.model_validate(repair_data)
            record_structured_output_metric(agent_name, True, repaired=True)
            return repaired_result


    except Exception as final_err:
        logger.error(f"Structured output completely failed for agent '{agent_name}' ({model_name}): {final_err}")
        record_structured_output_metric(agent_name, False)
        return None

