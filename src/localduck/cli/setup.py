"""Interactive setup wizard for LocalDuck."""

from __future__ import annotations

from pathlib import Path

import questionary
from rich.console import Console

from localduck.agents.detect import detect_copilot
from localduck.agents.manual import PROVIDER_MODELS, PROVIDER_NAMES
from localduck.config import ChecksConfig, LocalDuckConfig, save_config
from localduck.hooks.install import install_hook
from localduck.types import BlockOn, ProviderId, ReportFormat

console = Console()


def run_setup() -> None:
    """Run the interactive setup wizard."""
    console.print("\n🦆 [bold]LocalDuck Setup[/bold]\n")

    # Step 1: Detect Copilot
    copilot = detect_copilot()
    agent: str

    if copilot.available:
        console.print(f"  ✅ GitHub Copilot detected ({copilot.reason})\n")
        use_copilot = questionary.confirm(
            "Use GitHub Copilot for reviews?",
            default=True,
        ).ask()
        agent = "copilot" if use_copilot else "manual"
    else:
        console.print(f"  ⚠️  Copilot not available: {copilot.reason}")
        console.print("  Using manual provider mode.\n")
        agent = "manual"

    # Step 2: Provider selection (manual mode)
    provider: ProviderId | None = None
    model: str | None = None
    api_key: str | None = None

    if agent == "manual":
        provider_choices = [
            questionary.Choice(title=name, value=pid)
            for pid, name in PROVIDER_NAMES.items()
        ]
        provider = questionary.select(
            "Select AI provider:",
            choices=provider_choices,
        ).ask()

        if provider is None:
            console.print("[red]Setup cancelled.[/red]")
            return

        # Model selection
        models = PROVIDER_MODELS[provider]
        model_choices = [questionary.Choice(title=m, value=m) for m in models]
        model_choices.append(questionary.Choice(title="Enter custom model name", value="__custom__"))

        model = questionary.select(
            "Select model:",
            choices=model_choices,
        ).ask()

        if model == "__custom__":
            model = questionary.text("Enter model name:").ask()

        if model is None:
            console.print("[red]Setup cancelled.[/red]")
            return

        # API key
        api_key = questionary.password(
            f"Enter {PROVIDER_NAMES[provider]} API key:",
        ).ask()

        if not api_key:
            console.print("[red]API key is required for manual mode.[/red]")
            return

    # Step 3: Check selection
    console.print("\n[bold]Select checks to enable:[/bold]\n")

    check_options = [
        {"name": "Code Quality (style, complexity, dead code)", "value": "codeQuality", "checked": True},
        {"name": "Security (injection, secrets, insecure functions)", "value": "security", "checked": True},
        {"name": "Code Smell (large functions, nesting, magic numbers)", "value": "codeSmell", "checked": True},
        {"name": "Documentation (missing docstrings, undocumented APIs)", "value": "documentation", "checked": True},
        {"name": "License & Compliance", "value": "license", "checked": False},
        {"name": "Test Coverage", "value": "testCoverage", "checked": False},
        {"name": "Performance (N+1, memory leaks)", "value": "performance", "checked": False},
        {"name": "Accessibility (ARIA, semantic HTML)", "value": "accessibility", "checked": False},
        {"name": "AI/LLM-Specific (prompt injection)", "value": "llmSpecific", "checked": False},
    ]

    selected_checks = questionary.checkbox(
        "Enable checks:",
        choices=[
            questionary.Choice(title=opt["name"], value=opt["value"], checked=opt["checked"])
            for opt in check_options
        ],
    ).ask()

    if selected_checks is None:
        console.print("[red]Setup cancelled.[/red]")
        return

    # Step 4: Block on severity
    block_on: BlockOn = questionary.select(
        "Block commits on which severity?",
        choices=[
            questionary.Choice(title="Critical only", value="critical"),
            questionary.Choice(title="Warning and above", value="warning"),
            questionary.Choice(title="All issues", value="all"),
            questionary.Choice(title="Never block (report only)", value="none"),
        ],
        default="critical",
    ).ask()  # type: ignore[assignment]

    # Step 5: Report format
    report_format: ReportFormat = questionary.select(
        "Report format:",
        choices=[
            questionary.Choice(title="HTML", value="html"),
            questionary.Choice(title="Markdown", value="markdown"),
        ],
        default="html",
    ).ask()  # type: ignore[assignment]

    # Build config
    checks = ChecksConfig(
        **{opt["value"]: (opt["value"] in selected_checks) for opt in check_options}  # type: ignore[arg-type]
    )

    config = LocalDuckConfig(
        agent=agent,  # type: ignore[arg-type]
        provider=provider,
        model=model,
        api_key=api_key,
        block_on=block_on,
        checks=checks,
        report_format=report_format,
    )

    # Save config
    config_path = save_config(config)
    console.print(f"\n  ✅ Config written to [bold]{config_path}[/bold]")

    # Install pre-commit hook
    hook_path = install_hook()
    console.print(f"  ✅ Pre-commit hook installed at [bold]{hook_path}[/bold]")

    console.print("\n🦆 [bold green]Setup complete![/bold green] LocalDuck will scan on every commit.\n")
    console.print("  Run [bold]localduck scan[/bold] to test it now.\n")
