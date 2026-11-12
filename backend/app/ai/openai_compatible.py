"""OpenAI-compatible chat-completions provider.

Works with any endpoint that implements ``POST {base_url}/chat/completions``:
OpenAI, Groq, Together, vLLM, Ollama, and Google's Gemini compatibility endpoint.
Configuration is entirely via environment variables — no key is ever in code:

    NYAYMITRA_AI_PROVIDER=openai_compatible
    NYAYMITRA_AI_BASE_URL=https://api.openai.com/v1
    NYAYMITRA_AI_MODEL=gpt-4o-mini
    NYAYMITRA_AI_API_KEY=...            # never committed, never logged

If any of these is missing, ``available()`` is False and the RAG layer falls back to
the deterministic offline provider (or returns 503, depending on
``NYAYMITRA_AI_FALLBACK_MODE``).
"""
from __future__ import annotations

import json
import logging
import time

from ..config import Settings
from .base import AIProviderError, ProviderResult, ProviderUnavailable

log = logging.getLogger(__name__)


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, settings: Settings) -> None:
        self._base_url = (settings.ai_base_url or "").rstrip("/")
        self._api_key = settings.ai_api_key or ""
        self.model = settings.ai_model
        self._timeout = settings.ai_timeout_s
        self._attempts = max(1, settings.ai_max_attempts)
        self._backoff = max(0.0, settings.ai_retry_backoff_s)

    def available(self) -> bool:
        return bool(self._base_url and self._api_key and self.model)

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        temperature: float = 0.1,
    ) -> ProviderResult:
        if not self.available():
            raise ProviderUnavailable("provider is not configured")
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailable("httpx is not installed") from exc

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        response = None
        last_error: str | None = None
        for attempt in range(1, self._attempts + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(url, headers=headers, json=payload)
            except Exception as exc:  # noqa: BLE001 - network layer may raise many types
                last_error = type(exc).__name__
                log.warning("ai provider transport error (attempt %s/%s): %s",
                            attempt, self._attempts, last_error)
            else:
                status = response.status_code
                retryable = status == 429 or status >= 500
                if not retryable:
                    break
                last_error = f"HTTP {status}"
                log.warning("ai provider http error (attempt %s/%s): %s",
                            attempt, self._attempts, status)

            if attempt < self._attempts and self._backoff:
                time.sleep(self._backoff * attempt)

        if response is None:
            raise ProviderUnavailable(f"could not reach the AI provider ({last_error})")
        if response.status_code >= 400:
            raise ProviderUnavailable(f"AI provider returned HTTP {response.status_code}")
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            raise AIProviderError("malformed provider response") from exc
        if not text or not text.strip():
            raise AIProviderError("empty provider response")
        return ProviderResult(
            text=text.strip(),
            provider=self.name,
            model=self.model,
            usage=data.get("usage") if isinstance(data, dict) else None,
        )
