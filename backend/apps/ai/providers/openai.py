"""OpenAI provider."""

from __future__ import annotations

from collections.abc import Iterator

from apps.ai.providers.base import BaseLLMProvider, LLMResponse, ProviderError


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def _client(self):
        if not self.api_key:
            raise ProviderError(
                "OpenAI API key is not configured for this workspace."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("openai is not installed.") from exc
        return OpenAI(api_key=self.api_key)

    def generate(
        self, messages, *, temperature: float = 0.2, max_tokens: int = 1024
    ) -> LLMResponse:
        client = self._client()
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"OpenAI request failed: {exc}") from exc
        choice = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=choice.strip(),
            model=self.model,
            usage=usage.model_dump() if usage else None,
        )

    def stream(
        self, messages, *, temperature: float = 0.2, max_tokens: int = 1024
    ) -> Iterator[str]:
        client = self._client()
        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"OpenAI stream failed: {exc}") from exc
