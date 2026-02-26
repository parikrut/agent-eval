"""Filter non-reviewable files from the diff set."""

from __future__ import annotations

import re

from localduck.types import FileDiff

# File extensions that should never be reviewed
_SKIP_EXTENSIONS = frozenset({
    ".lock",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".bmp",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".map",
    ".min.js",
    ".min.css",
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".jar",
    ".war",
    ".zip",
    ".tar",
    ".gz",
    ".br",
})

# Filename patterns that should never be reviewed
_SKIP_PATTERNS = re.compile(
    r"(^|/)("
    r"package-lock\.json"
    r"|yarn\.lock"
    r"|pnpm-lock\.yaml"
    r"|Pipfile\.lock"
    r"|poetry\.lock"
    r"|uv\.lock"
    r"|Cargo\.lock"
    r"|Gemfile\.lock"
    r"|composer\.lock"
    r"|\.DS_Store"
    r"|Thumbs\.db"
    r")$"
)


def _should_skip(path: str) -> bool:
    """Return True if the file should be skipped based on path/extension."""
    lower = path.lower()

    # Check extensions
    for ext in _SKIP_EXTENSIONS:
        if lower.endswith(ext):
            return True

    # Check filename patterns
    if _SKIP_PATTERNS.search(path):
        return True

    return False


def filter_diffs(diffs: list[FileDiff]) -> tuple[list[FileDiff], list[str]]:
    """Separate reviewable diffs from skipped files.

    Returns:
        (reviewable, skipped_paths) tuple.
    """
    reviewable: list[FileDiff] = []
    skipped: list[str] = []

    for fd in diffs:
        if _should_skip(fd.path):
            skipped.append(fd.path)
        else:
            reviewable.append(fd)

    return reviewable, skipped
