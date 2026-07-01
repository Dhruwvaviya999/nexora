"""
LLM provider abstraction.

The rest of the app (RAG, summarizer, action items) talks only to this
interface, so the underlying model can be swapped per-workspace without touching
business logic. Concrete providers import their SDKs lazily.

Messages use the common chat shape: ``[{"role": "system|user|assistant",
"content": "..."}]``.
"""

from __future__ import annotations

import abc
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: dict | None = None


class ProviderError(Exception):
    """Raised when a provider can't fulfil a request (missing key, API error)."""


class BaseLLMProvider(abc.ABC):
    name: str = "base"

    def __init__(self, *, model: str, api_key: str = "", **kwargs):
        self.model = model
        self.api_key = api_key
        self.options = kwargs

    @abc.abstractmethod
    def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Return a single completion for ``messages``."""

    def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        """Yield response text incrementally.

        Default implementation falls back to a single non-streamed chunk so
        callers can be written against the streaming interface today; providers
        override this with true token streaming (the SSE upgrade path).
        """
        yield self.generate(
            messages, temperature=temperature, max_tokens=max_tokens
        ).text

    # -- helpers shared by concrete providers ------------------------------
    @staticmethod
    def _split_system(messages: list[dict]) -> tuple[str, list[dict]]:
        """Separate system messages (some SDKs take them out-of-band)."""
        system = "\n\n".join(
            m["content"] for m in messages if m.get("role") == "system"
        )
        rest = [m for m in messages if m.get("role") != "system"]
        return system, rest
