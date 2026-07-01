"""
Embedding provider factory.

Resolves the configured embedding provider. Today only the local Sentence
Transformers provider is implemented; Gemini/OpenAI embedders are recognised but
raise a clear error until their classes are added — so switching is a one-file
change (add the class, register it here) with no impact on the RAG pipeline.
"""

from __future__ import annotations

from django.conf import settings

from apps.knowledge.embeddings.base import BaseEmbeddingProvider
from apps.knowledge.embeddings.sentence_transformer import (
    SentenceTransformerProvider,
)

# Cache instances per (provider, model) — provider construction is cheap but the
# underlying model load is what we really want to reuse (handled inside the
# Sentence Transformers provider's module-level cache).
_INSTANCES: dict = {}

_NOT_IMPLEMENTED = {
    # provider key -> required dimension, so the mistake is obvious if someone
    # wires one up without also altering the pgvector column.
    "gemini": 768,
    "openai": 1536,
}


def get_embedding_provider(
    provider: str | None = None, model: str | None = None
) -> BaseEmbeddingProvider:
    provider = provider or settings.AI["DEFAULT_EMBEDDING_PROVIDER"]
    model = model or settings.AI["DEFAULT_EMBEDDING_MODEL"]

    cache_key = (provider, model)
    if cache_key in _INSTANCES:
        return _INSTANCES[cache_key]

    if provider == "sentence_transformer":
        instance: BaseEmbeddingProvider = SentenceTransformerProvider(model)
    elif provider in _NOT_IMPLEMENTED:
        raise NotImplementedError(
            f"Embedding provider '{provider}' is not implemented yet. It emits "
            f"{_NOT_IMPLEMENTED[provider]}-dim vectors, which also requires a "
            "migration altering DocumentChunk.embedding before it can be used."
        )
    else:
        raise ValueError(f"Unknown embedding provider: {provider!r}")

    _INSTANCES[cache_key] = instance
    return instance
