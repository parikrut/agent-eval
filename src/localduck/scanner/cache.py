"""ChromaDB-backed review cache for embedding-based lookup."""

from __future__ import annotations

import json
import time
from pathlib import Path

import chromadb
import numpy as np
import structlog

from localduck.types import Issue, Severity, CheckCategory

logger = structlog.get_logger()

_COLLECTION_NAME = "localduck_reviews"
_DEFAULT_CACHE_DIR = Path.home() / ".localduck" / "cache"


class ReviewCache:
    """Persistent cache of past review results indexed by diff embeddings."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(self._cache_dir))
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        """Number of entries in the cache."""
        return self._collection.count()

    def query(
        self,
        embedding: np.ndarray,
        threshold: float = 0.92,
    ) -> list[Issue] | None:
        """Look up a cached review result by embedding similarity.

        Returns the cached issues list if a match above `threshold` is found,
        otherwise None.
        """
        if self._collection.count() == 0:
            return None

        results = self._collection.query(
            query_embeddings=[embedding.tolist()],
            n_results=1,
            include=["distances", "metadatas"],
        )

        if not results["distances"] or not results["distances"][0]:
            return None

        # ChromaDB cosine distance = 1 - cosine_similarity
        distance = results["distances"][0][0]
        similarity = 1.0 - distance

        if similarity < threshold:
            return None

        # Deserialize stored issues
        metadata = results["metadatas"][0][0]  # type: ignore[index]
        issues_json = metadata.get("issues", "[]")  # type: ignore[union-attr]
        return _deserialize_issues(str(issues_json))

    def store(self, embedding: np.ndarray, issues: list[Issue], file_path: str) -> None:
        """Store a review result in the cache."""
        doc_id = f"{file_path}_{int(time.time() * 1000)}"
        self._collection.add(
            ids=[doc_id],
            embeddings=[embedding.tolist()],
            metadatas=[{
                "file_path": file_path,
                "issues": _serialize_issues(issues),
                "timestamp": int(time.time()),
            }],
            documents=[file_path],
        )

    def clear(self) -> int:
        """Clear all cached entries. Returns the number of entries deleted."""
        count = self._collection.count()
        self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return count

    def stats(self) -> dict[str, int | float]:
        """Return cache statistics."""
        return {
            "entries": self._collection.count(),
            "cache_dir": str(self._cache_dir),
        }


def _serialize_issues(issues: list[Issue]) -> str:
    """Serialize issues to JSON string for ChromaDB metadata storage."""
    return json.dumps([
        {
            "file": i.file,
            "line": i.line,
            "severity": i.severity.value,
            "category": i.category.value,
            "message": i.message,
            "suggestion": i.suggestion,
        }
        for i in issues
    ])


def _deserialize_issues(raw: str) -> list[Issue]:
    """Deserialize issues from JSON string."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    issues: list[Issue] = []
    for item in data:
        try:
            issues.append(
                Issue(
                    file=item["file"],
                    line=item.get("line"),
                    severity=Severity(item["severity"]),
                    category=CheckCategory(item["category"]),
                    message=item["message"],
                    suggestion=item.get("suggestion", ""),
                )
            )
        except (KeyError, ValueError):
            continue
    return issues
