"""Thin Gemini REST client with structured JSON output, retry and model fallback."""

import asyncio
import json
import logging
from typing import Any

import httpx

from .config import Settings

log = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRYABLE = {429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """Raised with a user-safe message when the LLM call cannot be completed."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


async def _call(client: httpx.AsyncClient, settings: Settings, model: str, body: dict) -> dict:
    resp = await client.post(
        GEMINI_URL.format(model=model),
        json=body,
        # Header (not query string) so the key never shows up in URL logs.
        headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()},
        timeout=settings.gemini_timeout_seconds,
    )
    if resp.status_code != 200:
        # Log status only; the body can echo parts of the prompt.
        log.warning("Gemini %s returned HTTP %s", model, resp.status_code)
        raise httpx.HTTPStatusError("gemini error", request=resp.request, response=resp)
    return resp.json()


def _parse(payload: dict) -> dict:
    candidates = payload.get("candidates") or []
    if not candidates:
        reason = (payload.get("promptFeedback") or {}).get("blockReason")
        raise LLMError(
            "The AI declined to process this input" + (f" ({reason})." if reason else "."), status_code=422
        )
    cand = candidates[0]
    if cand.get("finishReason") in {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST"}:
        raise LLMError("The AI declined to process this input. Please review the content and try again.", 422)
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("model returned malformed JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("model returned non-object JSON")
    return data


async def generate_json(
    settings: Settings,
    *,
    system: str,
    user: str,
    schema: dict,
    temperature: float = 0.4,
    client: httpx.AsyncClient | None = None,
) -> tuple[dict[str, Any], str]:
    """Return (parsed_json, model_used). Tries the primary model twice, then the fallback model."""
    if not settings.gemini_api_key.get_secret_value():
        raise LLMError("The server is missing its LLM API key. Please contact the site owner.", 503)

    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "responseSchema": schema,
            "maxOutputTokens": 8192,
        },
    }
    if settings.gemini_thinking_level:
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": settings.gemini_thinking_level}
    plan = [settings.gemini_model, settings.gemini_model]
    if settings.gemini_fallback_model and settings.gemini_fallback_model != settings.gemini_model:
        plan.append(settings.gemini_fallback_model)

    owns_client = client is None
    client = client or httpx.AsyncClient()
    last_status: int | None = None
    dead_models: set[str] = set()
    try:
        for attempt, model in enumerate(plan):
            if model in dead_models:
                continue
            try:
                return _parse(await _call(client, settings, model, body)), model
            except LLMError:
                raise
            except httpx.HTTPStatusError as exc:
                last_status = exc.response.status_code
                if last_status in (401, 403):
                    # A bad key won't be fixed by retrying.
                    raise LLMError("The AI service rejected the server's credentials.", 503) from exc
                # 400/404 are model-specific: skip this model and fall through to the fallback.
                if last_status in (400, 404):
                    dead_models.add(model)
                    continue
                if last_status not in RETRYABLE:
                    break
            except (httpx.TimeoutException, httpx.TransportError):
                last_status = 504
            except ValueError:
                last_status = 502  # malformed JSON — retry
            await asyncio.sleep(0.6 * (attempt + 1))
    finally:
        if owns_client:
            await client.aclose()

    if last_status == 429:
        raise LLMError("The AI service is busy right now (rate limited). Please try again in a minute.", 503)
    if last_status == 504:
        raise LLMError("The AI service took too long to respond. Please try again.", 504)
    raise LLMError("The AI service is temporarily unavailable. Please try again shortly.", 502)
