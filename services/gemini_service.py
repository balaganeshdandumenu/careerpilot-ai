import json
import logging

from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _classify_error(error):
    status = getattr(error, "status_code", None)
    message = str(error).casefold()
    if status in (401, 403) or "api key" in message or "permission" in message:
        return "authentication"
    if status == 429 or "quota" in message or "rate limit" in message:
        return "rate_limit"
    if status == 404 or "model" in message and "not found" in message:
        return "model_unavailable"
    if "timeout" in message or "timed out" in message:
        return "timeout"
    if status in (400, 422):
        return "invalid_request"
    if isinstance(error, errors.APIError):
        return "provider_unavailable"
    return "provider_error"


def generate_json(api_key, prompt, response_schema, model="gemini-3.8-flash"):
    if not api_key:
        raise AIServiceError("missing_key", "AI is not configured; the grounded plan is ready instead.")
    try:
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=15000))
        request_prompt = prompt
        for attempt in range(2):
            response = client.models.generate_content(
                model=model,
                contents=request_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.3,
                ),
            )
            text = response.text
            try:
                if not text:
                    raise json.JSONDecodeError("empty model response", "", 0)
                result = json.loads(text)
                if not isinstance(result, dict):
                    raise json.JSONDecodeError("expected a JSON object", text, 0)
                return result
            except json.JSONDecodeError as error:
                if attempt == 0:
                    logger.warning("Gemini returned empty or malformed structured output; retrying once")
                    request_prompt = prompt + "\nRegenerate the response as one valid JSON object matching the required schema. Do not include markdown or commentary."
                    continue
                code = "empty_response" if not text else "malformed_response"
                raise AIServiceError(code, "The AI response could not be validated.") from error
    except AIServiceError:
        raise
    except Exception as error:
        code = _classify_error(error)
        detail = str(error).replace(api_key, "[REDACTED]") if api_key else str(error)
        logger.error("Gemini request failed (%s, %s): %s", code, type(error).__name__, detail)
        raise AIServiceError(code, "The AI service could not complete this request.") from error