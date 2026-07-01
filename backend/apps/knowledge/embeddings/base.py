"""
Embedding provider abstraction.

Mirrors the LLM provider pattern (apps.ai.providers): a thin interface so the
RAG pipeline never depends on a concrete embedding backend. The default
implementation is local Sentence Transformers; Gemini/OpenAI embedders can be
added later by implementing this interface and registering them in the factory.

NOTE: every provider used with the existing pgvector column MUST emit vectors of
``settings.AI["EMBEDDING_DIM"]`` (384). A provider with a different dimension
requires a migration that alters ``DocumentChunk.embedding``.
"""

from __future__ import annotations

import abc


class BaseEmbeddingProvider(abc.ABC):
    """Turns text into fixed-size float vectors."""

    name: str = "base"

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the vectors this provider emits."""

    @abc.abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents. Returns one vector per input text."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string. Override if queries need special handling."""
        return self.embed_texts([text])[0]
