"""Ollama provider (local models over HTTP). No API key required."""

from __future__ import annotations

import json
from collections.abc import Iterator

from django.conf import settings

from apps.ai.providers.base import BaseLLMProvider, LLMResponse, ProviderError


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    @property
    def base_url(self) -> str:
        return (
            self.options.get("base_url")
            or settings.AI["OLLAMA_BASE_URL"]
        ).rstrip("/")

    def generate(
        self, messages, *, temperature: float = 0.2, max_tokens: int = 1024
    ) -> LLMResponse:
        import requests

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        return LLMResponse(
            text=(data.get("message", {}).get("content", "") or "").strip(),
            model=self.model,
        )

    def stream(
        self, messages, *, temperature: float = 0.2, max_tokens: int = 1024
    ) -> Iterator[str]:
        import requests

        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    piece = chunk.get("message", {}).get("content", "")
                    if piece:
                        yield piece
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Ollama stream failed: {exc}") from exc
