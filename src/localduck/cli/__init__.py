"""LocalDuck CLI — Typer entrypoint."""

from __future__ import annotations

import asyncio
import sys
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from localduck import __version__

app = typer.Typer(
    name="localduck",
    help="🦆 LocalDuck — Local AI-Powered Code Quality & Security Scanner",
    no_args_is_help=True,
    add_completion=False,
)
cache_app = typer.Typer(help="Manage the local embedding cache.")
app.add_typer(cache_app, name="cache")

console = Console()


@app.command()
def setup() -> None:
    """Interactive setup — configure provider, checks, and install pre-commit hook."""
    from localduck.cli.setup import run_setup

    run_setup()


@app.command()
def uninstall() -> None:
    """Remove the pre-commit hook and config."""
    from localduck.cli.uninstall import run_uninstall

    run_uninstall()


@app.command()
def scan(
    all_files: bool = typer.Option(False, "--all", help="Scan all tracked files, not just staged."),
) -> None:
    """Scan staged changes (or all files with --all) for issues."""
    from localduck.config import load_config
    from localduck.git import has_staged_changes
    from localduck.runner import run_scan

    config = load_config()

    if not all_files and not has_staged_changes():
        console.print("\n🦆 No staged changes to scan. Stage files with `git add` first.\n")
        raise typer.Exit(0)

    console.print("\n🦆 [bold]LocalDuck[/bold] scanning...\n")

    with console.status("[bold blue]Analyzing diffs...", spinner="dots"):
        result = asyncio.run(run_scan(config=config, scan_all=all_files))

    # Print summary table
    _print_summary(result)

    # Exit with non-zero if commit should be blocked
    if result.should_block(config.block_on):
        report_dir = Path(config.report_dir)
        console.print(
            f"\n🚫 [bold red]Commit blocked.[/bold red] See report in [bold]{report_dir}[/bold]\n"
        )
        raise typer.Exit(1)

    console.print("\n✅ [bold green]All clear![/bold green]\n")


@app.command()
def report() -> None:
    """Open the latest generated report in the browser."""
    from localduck.config import load_config
    from localduck.reports.generate import get_latest_report

    config = load_config()
    report_dir = Path(config.report_dir)
    latest = get_latest_report(report_dir)

    if latest is None:
        console.print("\n  No reports found. Run [bold]localduck scan[/bold] first.\n")
        raise typer.Exit(1)

    console.print(f"\n  Opening [bold]{latest}[/bold]...\n")
    webbrowser.open(latest.as_uri())


@cache_app.command("clear")
def cache_clear() -> None:
    """Wipe all cached review results."""
    from localduck.scanner.cache import ReviewCache

    cache = ReviewCache()
    count = cache.clear()
    console.print(f"\n  🗑️  Cleared {count} cached entries.\n")


@cache_app.command("stats")
def cache_stats() -> None:
    """Show cache statistics."""
    from localduck.scanner.cache import ReviewCache

    cache = ReviewCache()
    info = cache.stats()

    table = Table(title="🦆 Cache Stats")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in info.items():
        table.add_row(key, str(value))

    console.print()
    console.print(table)
    console.print()


@app.command()
def version() -> None:
    """Show the LocalDuck version."""
    console.print(f"localduck {__version__}")


def _print_summary(result) -> None:  # type: ignore[no-untyped-def]
    """Print a Rich summary of scan results to the console."""
    from localduck.types import CheckCategory, Severity

    if not result.issues:
        console.print("  ✅ [green]No issues found[/green]")
        return

    # Group by category
    from collections import defaultdict

    by_category: dict[str, list] = defaultdict(list)
    for issue in result.issues:
        by_category[issue.category.value].append(issue)

    category_labels = {
        "codeQuality": "Code Quality",
        "security": "Security",
        "codeSmell": "Code Smell",
        "license": "License & Compliance",
        "documentation": "Documentation",
        "testCoverage": "Test Coverage",
        "performance": "Performance",
        "accessibility": "Accessibility",
        "llmSpecific": "AI/LLM-Specific",
    }

    for cat_value, label in category_labels.items():
        issues = by_category.get(cat_value, [])
        if not issues:
            console.print(f"  ✔ {label:<20} [green]Passed[/green]")
        else:
            critical = sum(1 for i in issues if i.severity == Severity.CRITICAL)
            warning = sum(1 for i in issues if i.severity == Severity.WARNING)
            info_count = sum(1 for i in issues if i.severity == Severity.INFO)

            parts = []
            if critical:
                parts.append(f"[red]{critical} critical[/red]")
            if warning:
                parts.append(f"[yellow]{warning} warning[/yellow]")
            if info_count:
                parts.append(f"[blue]{info_count} info[/blue]")

            console.print(f"  ✗ {label:<20} {', '.join(parts)}")

            for issue in issues:
                loc = f"{issue.file}"
                if issue.line:
                    loc += f":{issue.line}"
                console.print(f"      └─ {loc:<25} {issue.message}")

    # Stats line
    stats_parts = [f"{result.files_scanned} files scanned"]
    if result.files_skipped:
        stats_parts.append(f"{result.files_skipped} skipped")
    if result.cache_hits:
        stats_parts.append(f"{result.cache_hits} cache hits")
    if result.files_deduped:
        stats_parts.append(f"{result.files_deduped} deduped")

    console.print(f"\n  [dim]{' · '.join(stats_parts)}[/dim]")
