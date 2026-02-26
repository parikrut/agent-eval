"""Git diff extraction and parsing utilities."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from localduck.types import FileDiff

# Regex to split a unified diff into per-file chunks
_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE)
_NEW_FILE_RE = re.compile(r"^new file mode", re.MULTILINE)
_DELETED_FILE_RE = re.compile(r"^deleted file mode", re.MULTILINE)


def _run_git(*args: str, cwd: Path | None = None) -> str:
    """Execute a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(msg)
    return result.stdout


def get_repo_root(cwd: Path | None = None) -> Path:
    """Return the root directory of the current git repository."""
    root = _run_git("rev-parse", "--show-toplevel", cwd=cwd).strip()
    return Path(root)


def get_staged_diff(cwd: Path | None = None) -> str:
    """Return the full unified diff of staged changes."""
    return _run_git("diff", "--staged", "--unified=3", cwd=cwd)


def get_all_diff(cwd: Path | None = None) -> str:
    """Return the diff of all tracked files against HEAD."""
    return _run_git("diff", "HEAD", "--unified=3", cwd=cwd)


def parse_diff_by_file(raw_diff: str) -> list[FileDiff]:
    """Split a unified diff string into per-file FileDiff objects."""
    if not raw_diff.strip():
        return []

    # Find all diff headers and their positions
    matches = list(_DIFF_HEADER_RE.finditer(raw_diff))
    if not matches:
        return []

    diffs: list[FileDiff] = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_diff)
        chunk = raw_diff[start:end]

        file_path = match.group(2)
        is_new = bool(_NEW_FILE_RE.search(chunk))
        is_deleted = bool(_DELETED_FILE_RE.search(chunk))

        diffs.append(
            FileDiff(
                path=file_path,
                diff=chunk.strip(),
                is_new=is_new,
                is_deleted=is_deleted,
            )
        )

    return diffs


def has_staged_changes(cwd: Path | None = None) -> bool:
    """Check if there are any staged changes."""
    result = subprocess.run(
        ["git", "diff", "--staged", "--quiet"],
        capture_output=True,
        cwd=cwd,
        check=False,
    )
    return result.returncode != 0
