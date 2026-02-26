"""Scan orchestrator — ties git, pipeline, adapter, and reports together."""

from __future__ import annotations

from pathlib import Path

import structlog

from localduck.agents import create_adapter
from localduck.config import LocalDuckConfig, load_config
from localduck.git import get_all_diff, get_staged_diff, parse_diff_by_file
from localduck.reports.generate import generate_report
from localduck.scanner.pipeline import run_pipeline
from localduck.types import ScanResult

logger = structlog.get_logger()


async def run_scan(
    config: LocalDuckConfig | None = None,
    scan_all: bool = False,
) -> ScanResult:
    """Execute a full scan and generate a report.

    Args:
        config: Config to use. Loads from .localduckrc if None.
        scan_all: If True, scan all tracked files instead of just staged changes.

    Returns:
        The complete ScanResult with all issues found.
    """
    cfg = config or load_config()

    # Get the diff
    raw_diff = get_all_diff() if scan_all else get_staged_diff()
    diffs = parse_diff_by_file(raw_diff)

    if not diffs:
        logger.info("no_changes_to_scan")
        return ScanResult()

    logger.info("scan_started", files=len(diffs), mode=cfg.agent)

    # Create the LLM adapter
    adapter = create_adapter(cfg)
    logger.info("adapter_ready", adapter=adapter.label)

    # Run the full pipeline
    result = await run_pipeline(diffs, adapter, cfg)

    # Generate report
    report_dir = Path(cfg.report_dir)
    report_path = generate_report(
        result=result,
        output_dir=report_dir,
        fmt=cfg.report_format,
    )
    logger.info("report_generated", path=str(report_path))

    return result
