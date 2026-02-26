"""Context-window-aware batching of file diffs."""

from __future__ import annotations

from localduck.types import FileDiff

# Approximate chars-per-token ratio (conservative for most models)
CHARS_PER_TOKEN = 4

# Security-sensitive path segments — files matching these are prioritized
_HIGH_RISK_SEGMENTS = frozenset({
    "auth",
    "secret",
    "crypto",
    "password",
    "credential",
    "token",
    "admin",
    "db",
    "database",
    "migrate",
    "env",
    "config",
    "permission",
    "rbac",
    "session",
    "oauth",
    "jwt",
    "key",
    "cert",
    "ssl",
    "tls",
})


def _risk_score(fd: FileDiff) -> int:
    """Higher score = higher priority for review. Security-sensitive files first."""
    path_lower = fd.path.lower()
    score = 0
    for segment in _HIGH_RISK_SEGMENTS:
        if segment in path_lower:
            score += 10
    # New files are higher risk than modifications
    if fd.is_new:
        score += 5
    return score


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN


def prioritize_diffs(diffs: list[FileDiff]) -> list[FileDiff]:
    """Sort diffs by risk score (descending) so security-sensitive files are reviewed first."""
    return sorted(diffs, key=_risk_score, reverse=True)


def batch_diffs(
    diffs: list[FileDiff],
    max_tokens_per_batch: int = 12_000,
    token_budget: int | None = None,
) -> tuple[list[list[FileDiff]], list[str]]:
    """Group diffs into batches that fit within context window limits.

    Args:
        diffs: Pre-prioritized list of file diffs.
        max_tokens_per_batch: Max tokens for a single LLM call.
        token_budget: Total token budget across all batches. None = unlimited.

    Returns:
        (batches, skipped_due_to_budget) tuple.
    """
    batches: list[list[FileDiff]] = []
    skipped: list[str] = []
    current_batch: list[FileDiff] = []
    current_tokens = 0
    total_tokens = 0

    for fd in diffs:
        diff_tokens = estimate_tokens(fd.diff)

        # Check total budget
        if token_budget is not None and total_tokens + diff_tokens > token_budget:
            skipped.append(fd.path)
            continue

        # If this diff alone exceeds a batch, put it in its own batch
        if diff_tokens > max_tokens_per_batch:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            batches.append([fd])
            total_tokens += diff_tokens
            continue

        # If adding this diff would overflow the current batch, flush it
        if current_tokens + diff_tokens > max_tokens_per_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(fd)
        current_tokens += diff_tokens
        total_tokens += diff_tokens

    if current_batch:
        batches.append(current_batch)

    return batches, skipped
