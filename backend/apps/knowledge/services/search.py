"""
Semantic search service — the retrieval half of the RAG pipeline.

Embeds the query and runs a pgvector cosine-distance nearest-neighbour search,
**always filtered by workspace** so retrieval can never cross the tenant
boundary. Returns ranked results carrying a normalised similarity score.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from pgvector.django import CosineDistance

from apps.knowledge.embeddings import get_embedding_provider
from apps.knowledge.models import DocumentChunk


@dataclass
class SearchResult:
    chunk: DocumentChunk
    distance: float

    @property
    def score(self) -> float:
        """Cosine similarity in [0, 1] (1 = identical)."""
        return round(max(0.0, 1.0 - self.distance), 4)


def semantic_search(
    *,
    workspace,
    query: str,
    limit: int | None = None,
    max_distance: float | None = None,
) -> list[SearchResult]:
    """Return the most relevant chunks for ``query`` within ``workspace``."""
    query = (query or "").strip()
    if not query:
        return []

    limit = limit or settings.AI["SEARCH_TOP_K"]
    max_distance = (
        max_distance if max_distance is not None else settings.AI["SEARCH_MAX_DISTANCE"]
    )

    provider = get_embedding_provider()
    query_vector = provider.embed_query(query)

    qs = (
        DocumentChunk.objects.filter(
            workspace=workspace, embedding__isnull=False
        )
        .annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lte=max_distance)
        .select_related("document")
        .order_by("distance")[:limit]
    )

    return [SearchResult(chunk=c, distance=float(c.distance)) for c in qs]
