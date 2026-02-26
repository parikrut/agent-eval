"""Full scan pipeline: filter → embed → cache → dedup → batch → review → store."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from localduck.scanner.batcher import batch_diffs, prioritize_diffs
from localduck.scanner.cache import ReviewCache
from localduck.scanner.dedup import deduplicate
from localduck.scanner.embedder import embed_text
from localduck.scanner.filter import filter_diffs
from localduck.types import FileDiff, Issue, ScanResult

if TYPE_CHECKING:
    from localduck.agents.base import BaseAdapter
    from localduck.config import LocalDuckConfig

logger = structlog.get_logger()


async def run_pipeline(
    diffs: list[FileDiff],
    adapter: BaseAdapter,
    config: LocalDuckConfig,
) -> ScanResult:
    """Execute the full scan pipeline on a set of file diffs.

    Steps:
    1. Filter out non-reviewable files
    2. Prioritize by risk surface
    3. Deduplicate near-identical diffs
    4. Check embedding cache for already-reviewed diffs
    5. Batch remaining diffs within context window limits
    6. Send batches to LLM concurrently (with concurrency limit)
    7. Store results in cache
    8. Merge and return all issues
    """
    result = ScanResult()

    # Step 1: Filter
    reviewable, skipped_paths = filter_diffs(diffs)
    result.files_skipped = len(skipped_paths)
    result.skipped_files = skipped_paths
    logger.info("filter_complete", reviewable=len(reviewable), skipped=len(skipped_paths))

    if not reviewable:
        return result

    # Step 2: Prioritize
    reviewable = prioritize_diffs(reviewable)

    # Step 3: Deduplicate
    dedup_result = deduplicate(reviewable, threshold=config.cache_threshold)
    result.files_deduped = sum(len(dupes) for dupes in dedup_result.groups.values())
    logger.info(
        "dedup_complete",
        unique=len(dedup_result.unique),
        deduped=result.files_deduped,
    )

    # Step 4: Cache check
    cache = ReviewCache()
    needs_review: list[FileDiff] = []
    needs_review_embeddings: list[object] = []
    cached_issues: list[Issue] = []

    for fd, embedding in zip(dedup_result.unique, dedup_result.embeddings):
        cached = cache.query(embedding, threshold=config.cache_threshold)
        if cached is not None:
            cached_issues.extend(cached)
            result.cache_hits += 1
            result.files_cached += 1
            logger.debug("cache_hit", file=fd.path)
        else:
            needs_review.append(fd)
            needs_review_embeddings.append(embedding)

    logger.info(
        "cache_check_complete",
        hits=result.cache_hits,
        misses=len(needs_review),
    )

    # Step 5: Batch
    token_budget = config.token_budget if config.token_budget > 0 else None
    batches, budget_skipped = batch_diffs(
        needs_review,
        token_budget=token_budget,
    )
    result.skipped_files.extend(budget_skipped)
    result.files_scanned = len(reviewable) - len(budget_skipped)

    logger.info(
        "batching_complete",
        batches=len(batches),
        budget_skipped=len(budget_skipped),
    )

    # Step 6: Review batches concurrently with semaphore
    semaphore = asyncio.Semaphore(config.max_concurrent)
    all_issues: list[Issue] = list(cached_issues)

    async def _review_batch(batch: list[FileDiff], batch_idx: int) -> list[Issue]:
        async with semaphore:
            logger.debug("reviewing_batch", batch=batch_idx, files=len(batch))
            return await adapter.review(batch)

    tasks = [_review_batch(batch, i) for i, batch in enumerate(batches)]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, batch_result in enumerate(batch_results):
        if isinstance(batch_result, Exception):
            logger.error("batch_review_failed", batch=i, error=str(batch_result))
            continue
        all_issues.extend(batch_result)

    # Step 7: Store results in cache
    _store_in_background(cache, needs_review, needs_review_embeddings, all_issues)

    # Step 8: Propagate issues to deduplicated files
    for representative_path, duplicate_paths in dedup_result.groups.items():
        rep_issues = [i for i in all_issues if i.file == representative_path]
        for dup_path in duplicate_paths:
            for issue in rep_issues:
                all_issues.append(
                    Issue(
                        file=dup_path,
                        line=issue.line,
                        severity=issue.severity,
                        category=issue.category,
                        message=issue.message,
                        suggestion=issue.suggestion,
                    )
                )

    result.issues = all_issues
    return result


def _store_in_background(
    cache: ReviewCache,
    diffs: list[FileDiff],
    embeddings: list[object],
    all_issues: list[Issue],
) -> None:
    """Store review results back into the embedding cache."""
    import numpy as np

    for fd, embedding in zip(diffs, embeddings):
        file_issues = [i for i in all_issues if i.file == fd.path]
        if isinstance(embedding, np.ndarray):
            cache.store(embedding, file_issues, fd.path)
