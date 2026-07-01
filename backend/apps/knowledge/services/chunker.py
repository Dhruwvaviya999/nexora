"""
Chunking strategy.

A word-window splitter with overlap: documents are split into overlapping
windows of ~``CHUNK_SIZE_WORDS`` words so that context spanning a boundary is
still retrievable. This is deliberately dependency-free and deterministic; a
token-accurate splitter (tiktoken / model tokenizer) can replace this later
without changing the interface.

``token_count`` is a word-count approximation — good enough for budgeting and
display; it is not used for billing.
"""

from __future__ import annotations

import re

from django.conf import settings

_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", (text or "")).strip()


def chunk_text(
    text: str,
    *,
    size: int | None = None,
    overlap: int | None = None,
) -> list[dict]:
    """Split ``text`` into overlapping chunks.

    Returns a list of ``{"content", "chunk_index", "token_count"}`` dicts.
    """
    size = size or settings.AI["CHUNK_SIZE_WORDS"]
    overlap = overlap if overlap is not None else settings.AI["CHUNK_OVERLAP_WORDS"]
    if overlap >= size:
        overlap = size // 4  # guard against a non-advancing window

    normalized = _normalize(text)
    if not normalized:
        return []

    words = normalized.split(" ")
    step = size - overlap
    chunks: list[dict] = []
    index = 0
    for start in range(0, len(words), step):
        window = words[start : start + size]
        if not window:
            break
        content = " ".join(window)
        chunks.append(
            {
                "content": content,
                "chunk_index": index,
                "token_count": len(window),
            }
        )
        index += 1
        if start + size >= len(words):
            break
    return chunks
