"""Uninstall LocalDuck — remove hook and config."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from localduck.config import CONFIG_FILENAME
from localduck.git import get_repo_root

console = Console()


def run_uninstall() -> None:
    """Remove the pre-commit hook and .localduckrc config."""
    removed_anything = False

    # Remove pre-commit hook
    try:
        repo_root = get_repo_root()
        hook_path = repo_root / ".git" / "hooks" / "pre-commit"
        if hook_path.is_file():
            content = hook_path.read_text(encoding="utf-8")
            if "localduck" in content.lower():
                hook_path.unlink()
                console.print(f"  ✅ Removed pre-commit hook: [bold]{hook_path}[/bold]")
                removed_anything = True
            else:
                console.print("  ⚠️  Pre-commit hook exists but wasn't installed by LocalDuck — skipped.")
        else:
            console.print("  ℹ️  No pre-commit hook found.")
    except RuntimeError:
        console.print("  ⚠️  Not inside a git repository — skipping hook removal.")

    # Remove config
    config_path = Path.cwd() / CONFIG_FILENAME
    if config_path.is_file():
        config_path.unlink()
        console.print(f"  ✅ Removed config: [bold]{config_path}[/bold]")
        removed_anything = True
    else:
        console.print("  ℹ️  No .localduckrc found.")

    if removed_anything:
        console.print("\n🦆 [bold]LocalDuck uninstalled.[/bold]\n")
    else:
        console.print("\n  Nothing to remove.\n")
