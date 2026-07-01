"""
Knowledge models — the retrieval layer of the RAG pipeline.

``DocumentChunk`` stores a slice of an extracted document together with its
embedding vector (pgvector). ``EmbeddingJob`` tracks the lifecycle of processing
a document so the frontend can show progress and failures.

Both carry an explicit ``workspace`` FK (denormalised from the document) so the
tenant boundary can be enforced with a single indexed filter on similarity
queries — the hot path for semantic search.
"""

from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.common.models import BaseModel

EMBEDDING_DIM = settings.AI["EMBEDDING_DIM"]


class DocumentChunk(BaseModel):
    """A single embedded slice of a document's extracted text."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="document_chunks",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    content = models.TextField()
    chunk_index = models.PositiveIntegerField()
    token_count = models.PositiveIntegerField(default=0)
    # Nullable so a chunk row can exist before its embedding is computed.
    embedding = VectorField(dimensions=EMBEDDING_DIM, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("document", "chunk_index")
        constraints = [
            models.UniqueConstraint(
                fields=("document", "chunk_index"),
                name="unique_document_chunk_index",
            )
        ]
        indexes = [
            models.Index(fields=["workspace"]),
            # Approximate-nearest-neighbour index for cosine similarity search.
            HnswIndex(
                name="documentchunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document_id} #{self.chunk_index}"


class EmbeddingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class EmbeddingJob(BaseModel):
    """Tracks (re)processing of a single document into chunks + embeddings."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="embedding_jobs",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="embedding_jobs",
    )
    status = models.CharField(
        max_length=20,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING,
    )
    error = models.TextField(blank=True, default="")
    chunk_count = models.PositiveIntegerField(default=0)
    provider = models.CharField(max_length=64, blank=True, default="")
    model = models.CharField(max_length=128, blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["document", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"EmbeddingJob({self.document_id}, {self.status})"
