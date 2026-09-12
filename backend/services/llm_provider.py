"""Small OpenAI-compatible text provider adapter.

No provider-specific package is required: the adapter speaks the standard
``/chat/completions`` JSON contract through httpx. OpenRouter can be forced for
research/localization even while Gemini remains the default assistant provider.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

from backend.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL_FAST,
    OPENROUTER_MODEL_QUALITY,
    OPENROUTER_TIMEOUT_SECONDS,
)

logger = logging.getLogger("elarax.llm_provider")


class LLMProviderService:
    def __init__(self) -> None:
        # A short, non-sensitive diagnostic is useful to the research agent
        # and logs without ever exposing prompts or credentials.
        self.last_error: str | None = None

    def configured(self, *, force_openrouter: bool = False) -> bool:
        if os.getenv("AETHERBOT_TESTING") == "1":
            return False
        if force_openrouter:
            return bool(OPENROUTER_API_KEY)
        return LLM_PROVIDER in {"openai", "openai-compatible", "openrouter"} and bool(
            LLM_API_KEY or OPENROUTER_API_KEY
        )

    def _settings(self, *, force_openrouter: bool, model: str | None) -> tuple[str, str, str]:
        if force_openrouter or LLM_PROVIDER == "openrouter":
            return (
                OPENROUTER_API_KEY or LLM_API_KEY,
                OPENROUTER_BASE_URL,
                model or OPENROUTER_MODEL_QUALITY,
            )
        return (LLM_API_KEY, LLM_BASE_URL, model or LLM_MODEL)

    def generate_text(
        self,
        *,
        prompt: str,
        instruction: str,
        max_output_tokens: int = 700,
        force_openrouter: bool = False,
        model: str | None = None,
    ) -> str | None:
        self.last_error = None
        if not self.configured(force_openrouter=force_openrouter):
            self.last_error = "not_configured"
            return None
        api_key, base_url, selected_model = self._settings(
            force_openrouter=force_openrouter, model=model
        )
        # If a quality and fast model are both configured, a provider/model
        # rejection can fall through to the fast model without changing the
        # rest of the research pipeline. Duplicate model names are attempted
        # only once.
        models = [selected_model]
        if force_openrouter and selected_model == OPENROUTER_MODEL_QUALITY:
            if OPENROUTER_MODEL_FAST and OPENROUTER_MODEL_FAST not in models:
                models.append(OPENROUTER_MODEL_FAST)
        for candidate_model in models:
            try:
                response = httpx.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        **(
                            {
                                "HTTP-Referer": "http://localhost:3000",
                                "X-Title": "ElaraX Market Research",
                            }
                            if force_openrouter or LLM_PROVIDER == "openrouter"
                            else {}
                        ),
                    },
                    json={
                        "model": candidate_model,
                        "messages": [
                            {"role": "system", "content": instruction},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_output_tokens,
                    },
                    timeout=OPENROUTER_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                choices = response.json().get("choices") or []
                content = ((choices[0].get("message") or {}).get("content") if choices else None)
                if content:
                    return str(content).strip()
                self.last_error = "empty_response"
            except httpx.HTTPStatusError as exc:
                self.last_error = f"http_{exc.response.status_code}"
                logger.warning(
                    "LLM provider rejected %s request with HTTP %s",
                    candidate_model,
                    exc.response.status_code,
                )
            except httpx.RequestError as exc:
                self.last_error = "network_error"
                logger.warning("LLM provider request failed for %s: %s", candidate_model, type(exc).__name__)
            except (ValueError, TypeError, KeyError):
                self.last_error = "invalid_response"
                logger.warning("LLM provider returned an invalid response for %s", candidate_model)
        return None

    def generate_json(
        self,
        *,
        prompt: str,
        instruction: str,
        max_output_tokens: int = 1_200,
        model: str | None = None,
    ) -> dict[str, Any] | None:
        """Request JSON from OpenRouter and tolerate fenced/plain JSON output."""

        models = [model or OPENROUTER_MODEL_QUALITY]
        if not model and OPENROUTER_MODEL_FAST and OPENROUTER_MODEL_FAST not in models:
            models.append(OPENROUTER_MODEL_FAST)
        for candidate_model in models:
            content = self.generate_text(
                prompt=prompt,
                instruction=(
                    f"{instruction}\nReturn only one valid JSON object. Do not include markdown fences."
                ),
                max_output_tokens=max_output_tokens,
                force_openrouter=True,
                model=candidate_model,
            )
            if not content:
                continue
            cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            candidates = [cleaned]
            candidates.extend(re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.I))
            decoder = json.JSONDecoder()
            for index, char in enumerate(cleaned):
                if char == "{":
                    try:
                        _, end = decoder.raw_decode(cleaned[index:])
                        candidates.append(cleaned[index : index + end])
                    except json.JSONDecodeError:
                        continue
            for candidate in candidates:
                try:
                    parsed = json.loads(candidate)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(parsed, dict):
                    return parsed
            self.last_error = "invalid_json"
        return None


llm_provider_service = LLMProviderService()
