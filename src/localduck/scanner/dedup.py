"""Batch deduplication — group near-identical diffs before review."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import structlog

from localduck.scanner.embedder import cosine_similarity, embed_texts
from localduck.types import FileDiff

logger = structlog.get_logger()


@dataclass
class DedupResult:
    """Result of deduplication across a batch of diffs."""

    # Unique diffs that need individual review
    unique: list[FileDiff] = field(default_factory=list)
    # Map: representative FileDiff path → list of duplicate FileDiff paths
    groups: dict[str, list[str]] = field(default_factory=dict)
    # Embeddings for the unique diffs, in same order as `unique`
    embeddings: list[np.ndarray] = field(default_factory=list)


def deduplicate(
    diffs: list[FileDiff],
    threshold: float = 0.95,
) -> DedupResult:
    """Find near-duplicate diffs within a batch.

    Diffs with cosine similarity above `threshold` are grouped together.
    Only the first member of each group is marked as unique (needs review).
    """
    if not diffs:
        return DedupResult()

    if len(diffs) == 1:
        embeddings = embed_texts([diffs[0].diff])
        return DedupResult(
            unique=list(diffs),
            groups={},
            embeddings=[embeddings[0]],
        )

    # Embed all diffs in one batch call
    texts = [fd.diff for fd in diffs]
    all_embeddings = embed_texts(texts)

    assigned: set[int] = set()
    unique: list[FileDiff] = []
    unique_embeddings: list[np.ndarray] = []
    groups: dict[str, list[str]] = {}

    for i in range(len(diffs)):
        if i in assigned:
            continue

        assigned.add(i)
        unique.append(diffs[i])
        unique_embeddings.append(all_embeddings[i])
        duplicates: list[str] = []

        # Check remaining diffs against this representative
        for j in range(i + 1, len(diffs)):
            if j in assigned:
                continue
            sim = cosine_similarity(all_embeddings[i], all_embeddings[j])
            if sim >= threshold:
                assigned.add(j)
                duplicates.append(diffs[j].path)

        if duplicates:
            groups[diffs[i].path] = duplicates

    logger.debug(
        "dedup_complete",
        total=len(diffs),
        unique=len(unique),
        groups=len(groups),
    )

    return DedupResult(unique=unique, groups=groups, embeddings=unique_embeddings)
