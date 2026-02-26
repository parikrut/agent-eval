"""Pre-commit hook installer."""

from __future__ import annotations

import stat
from pathlib import Path

from localduck.git import get_repo_root

_HOOK_CONTENT = """\
#!/bin/sh
# LocalDuck pre-commit hook — scans staged changes before committing.
# Installed by `localduck setup`. Remove with `localduck uninstall`.

localduck scan
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo ""
    echo "🦆 LocalDuck blocked the commit. Fix the issues above or run:"
    echo "   git commit --no-verify   # to skip the scan"
    echo ""
fi

exit $exit_code
"""


def install_hook(repo_root: Path | None = None) -> Path:
    """Install the LocalDuck pre-commit hook.

    Args:
        repo_root: Root of the git repo. Auto-detected if None.

    Returns:
        Path to the installed hook file.
    """
    root = repo_root or get_repo_root()
    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "pre-commit"

    # Check for existing hook not installed by us
    if hook_path.is_file():
        existing = hook_path.read_text(encoding="utf-8")
        if "localduck" not in existing.lower():
            # Rename existing hook so we don't destroy user's work
            backup = hook_path.with_suffix(".pre-localduck")
            hook_path.rename(backup)

    hook_path.write_text(_HOOK_CONTENT, encoding="utf-8")

    # Make executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    return hook_path
