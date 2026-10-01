import json
import logging
from pathlib import Path

from google.genai import types

from services.gemini_service import AIServiceError, generate_json

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "resume_prompt.txt"


def enrich_recommendations(analysis, role, api_key):
    if not api_key:
        return "deterministic"
    facts = {
        "target_role": role["title"],
        "skills_detected": analysis["skills"],
        "role_skills_matched": analysis["matched"],
        "role_skills_not_detected": analysis["missing"],
        "recommendations": [
            {"priority": item["priority"], "problem": item["problem"]}
            for item in analysis["recommendations"]
        ],
    }
    item_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "priority": types.Schema(type=types.Type.STRING, enum=["high", "medium", "low"]),
            "why": types.Schema(type=types.Type.STRING),
            "action": types.Schema(type=types.Type.STRING),
        },
        required=["priority", "why", "action"],
    )
    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={"recommendations": types.Schema(type=types.Type.ARRAY, items=item_schema)},
        required=["recommendations"],
    )
    prompt = PROMPT_PATH.read_text(encoding="utf-8").replace("{{FACTS}}", json.dumps(facts))
    try:
        response = generate_json(api_key, prompt, response_schema)
        items = response.get("recommendations")
        if not isinstance(items, list) or len(items) != len(analysis["recommendations"]):
            logger.warning("Resume recommendations failed schema validation; using deterministic text")
            return "malformed_fallback"
        for original, enriched in zip(analysis["recommendations"], items):
            if not isinstance(enriched, dict):
                return "malformed_fallback"
            if enriched.get("priority") != original["priority"]:
                return "malformed_fallback"
            why = enriched.get("why")
            action = enriched.get("action")
            if not isinstance(why, str) or not 15 <= len(why) <= 240 or not isinstance(action, str) or not 15 <= len(action) <= 280:
                return "malformed_fallback"
        for original, enriched in zip(analysis["recommendations"], items):
            original["why"] = enriched["why"]
            original["action"] = enriched["action"]
        return "ready"
    except AIServiceError as error:
        logger.warning("Resume report uses deterministic recommendations; AI status=%s", error.code)
        return error.code