"""Report generation — HTML and Markdown via Jinja2."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, PackageLoader

from localduck.types import Issue, ReportFormat, ScanResult, Severity

_env = Environment(
    loader=PackageLoader("localduck.reports", "templates"),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _group_issues_by_file(issues: list[Issue]) -> dict[str, list[Issue]]:
    """Group issues by file path, preserving insertion order."""
    grouped: dict[str, list[Issue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.file].append(issue)
    return dict(grouped)


def _severity_counts(issues: list[Issue]) -> dict[str, int]:
    """Count issues by severity level."""
    counts = {"critical": 0, "warning": 0, "info": 0}
    for issue in issues:
        counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
    return counts


def generate_report(
    result: ScanResult,
    output_dir: Path,
    fmt: ReportFormat = "html",
) -> Path:
    """Generate a report file and return its path.

    Args:
        result: The scan result containing all issues.
        output_dir: Directory to write the report into.
        fmt: Report format — "html" or "markdown".

    Returns:
        Path to the generated report file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")

    template_name = "report.html.j2" if fmt == "html" else "report.md.j2"
    extension = ".html" if fmt == "html" else ".md"

    template = _env.get_template(template_name)
    content = template.render(
        result=result,
        issues_by_file=_group_issues_by_file(result.issues),
        counts=_severity_counts(result.issues),
        timestamp=timestamp,
    )

    report_path = output_dir / f"report-{date_slug}{extension}"
    report_path.write_text(content, encoding="utf-8")

    return report_path


def get_latest_report(report_dir: Path) -> Path | None:
    """Find the most recent report file in the given directory."""
    if not report_dir.is_dir():
        return None

    reports = sorted(
        report_dir.glob("report-*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return reports[0] if reports else None
