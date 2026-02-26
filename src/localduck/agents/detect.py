"""Copilot (GitHub Models API) auto-detection."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class CopilotStatus:
    """Result of Copilot detection."""

    available: bool
    token: str | None = None
    reason: str = ""


def detect_copilot() -> CopilotStatus:
    """Check if GitHub Copilot is usable via `gh` CLI or GITHUB_TOKEN."""
    # 1. Check environment variable
    env_token = os.environ.get("GITHUB_TOKEN")
    if env_token:
        logger.debug("copilot_detected_via_env")
        return CopilotStatus(available=True, token=env_token, reason="GITHUB_TOKEN env")

    # 2. Try gh auth token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            token = result.stdout.strip()
            logger.debug("copilot_detected_via_gh_cli")
            return CopilotStatus(available=True, token=token, reason="gh auth token")
    except FileNotFoundError:
        return CopilotStatus(available=False, reason="gh CLI not installed")
    except subprocess.TimeoutExpired:
        return CopilotStatus(available=False, reason="gh auth token timed out")

    return CopilotStatus(available=False, reason="gh CLI not authenticated")
