"""
Default embedding provider: local Sentence Transformers (all-MiniLM-L6-v2).

The model is heavy to load (pulls in torch) so it is loaded lazily and cached as
a module-level singleton — the first embed call pays the cost, every call after
reuses the in-memory model. No network or API key required.
"""

from __future__ import annotations

from django.conf import settings

from apps.knowledge.embeddings.base import BaseEmbeddingProvider

# Cache loaded models by name so multiple providers/threads share one instance.
_MODELS: dict = {}


def _load_model(model_name: str):
    model = _MODELS.get(model_name)
    if model is None:
        # Imported lazily so the dependency is only required when embeddings run.
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        _MODELS[model_name] = model
    return model


class SentenceTransformerProvider(BaseEmbeddingProvider):
    name = "sentence_transformer"

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.AI["DEFAULT_EMBEDDING_MODEL"]
        self._dimension = settings.AI["EMBEDDING_DIM"]

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = _load_model(self.model_name)
        vectors = model.encode(
            texts,
            batch_size=settings.AI["EMBED_BATCH_SIZE"],
            normalize_embeddings=True,  # unit vectors -> cosine distance is stable
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]
