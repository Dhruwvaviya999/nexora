"""Google Gemini provider (default)."""

from __future__ import annotations

from collections.abc import Iterator

from apps.ai.providers.base import BaseLLMProvider, LLMResponse, ProviderError


class GeminiProvider(BaseLLMProvider):
    name = "gemini"

    def _client(self):
        if not self.api_key:
            raise ProviderError(
                "Gemini API key is not configured for this workspace."
            )
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                "google-generativeai is not installed."
            ) from exc
        genai.configure(api_key=self.api_key)
        return genai

    @staticmethod
    def _to_contents(messages: list[dict]) -> list[dict]:
        # Gemini uses roles "user"/"model" and a "parts" list.
        contents = []
        for m in messages:
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [m.get("content", "")]})
        return contents

    def generate(
        self, messages, *, temperature: float = 0.2, max_tokens: int = 1024
    ) -> LLMResponse:
        genai = self._client()
        system, rest = self._split_system(messages)
        model = genai.GenerativeModel(
            self.model,
            system_instruction=system or None,
        )
        try:
            resp = model.generate_content(
                self._to_contents(rest),
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Gemini request failed: {exc}") from exc
        return LLMResponse(text=(resp.text or "").strip(), model=self.model)

    def stream(
        self, messages, *, temperature: float = 0.2, max_tokens: int = 1024
    ) -> Iterator[str]:
        genai = self._client()
        system, rest = self._split_system(messages)
        model = genai.GenerativeModel(self.model, system_instruction=system or None)
        try:
            for chunk in model.generate_content(
                self._to_contents(rest),
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
                stream=True,
            ):
                if getattr(chunk, "text", ""):
                    yield chunk.text
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Gemini stream failed: {exc}") from exc
