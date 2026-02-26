"""Local embedding via sentence-transformers."""

from __future__ import annotations

import numpy as np
import structlog

logger = structlog.get_logger()

# Lazy-loaded model singleton
_model = None
_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():  # type: ignore[no-untyped-def]
    """Lazy-load the sentence-transformers model on first use."""
    global _model  # noqa: PLW0603
    if _model is None:
        logger.info("loading_embedding_model", model=_MODEL_NAME)
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_text(text: str) -> np.ndarray:
    """Embed a single text string into a vector."""
    model = _get_model()
    vector: np.ndarray = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
    return vector


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed multiple texts into a matrix of vectors."""
    model = _get_model()
    vectors: np.ndarray = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return vectors


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
