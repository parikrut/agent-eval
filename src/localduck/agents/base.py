"""Abstract base adapter with prompt building and response parsing."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import structlog

from localduck.types import CheckCategory, FileDiff, Issue, Severity

if TYPE_CHECKING:
    from localduck.config import LocalDuckConfig

logger = structlog.get_logger()

# Display names for check categories used in prompts
_CHECK_LABELS: dict[CheckCategory, str] = {
    CheckCategory.CODE_QUALITY: "Code Quality",
    CheckCategory.SECURITY: "Security",
    CheckCategory.CODE_SMELL: "Code Smell",
    CheckCategory.LICENSE: "License & Compliance",
    CheckCategory.DOCUMENTATION: "Documentation",
    CheckCategory.TEST_COVERAGE: "Test Coverage",
    CheckCategory.PERFORMANCE: "Performance",
    CheckCategory.ACCESSIBILITY: "Accessibility",
    CheckCategory.LLM_SPECIFIC: "AI/LLM-Specific",
}


def build_system_prompt(categories: list[CheckCategory]) -> str:
    """Build the system prompt describing the reviewer's role."""
    check_list = "\n".join(f"- {_CHECK_LABELS[c]}" for c in categories)
    return (
        "You are a senior code reviewer performing an automated pre-commit review.\n"
        "Analyze the provided git diff and find issues in these categories:\n"
        f"{check_list}\n\n"
        "For each issue found, respond with a JSON array of objects. Each object must have:\n"
        '  "file": string (file path),\n'
        '  "line": number or null (line number if identifiable),\n'
        '  "severity": "critical" | "warning" | "info",\n'
        '  "category": one of the check category identifiers,\n'
        '  "message": string (concise description of the issue),\n'
        '  "suggestion": string (how to fix it, or empty string)\n\n'
        "If no issues are found, respond with an empty JSON array: []\n"
        "Respond ONLY with the JSON array — no markdown fences, no explanation."
    )


def build_review_prompt(diffs: list[FileDiff]) -> str:
    """Build the user prompt containing the diffs to review."""
    parts: list[str] = []
    for fd in diffs:
        parts.append(f"=== {fd.path} ===\n{fd.diff}")
    return "\n\n".join(parts)


def parse_review_response(raw: str) -> list[Issue]:
    """Parse the LLM response into a list of Issue objects."""
    # Strip markdown fences if present
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    if not cleaned or cleaned == "[]":
        return []

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("failed_to_parse_llm_response", raw=raw[:200])
        return []

    if not isinstance(data, list):
        logger.warning("llm_response_not_array", raw=raw[:200])
        return []

    issues: list[Issue] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            issues.append(
                Issue(
                    file=str(item.get("file", "unknown")),
                    line=item.get("line"),
                    severity=Severity(item.get("severity", "info")),
                    category=CheckCategory(item.get("category", "codeQuality")),
                    message=str(item.get("message", "")),
                    suggestion=str(item.get("suggestion", "")),
                )
            )
        except (ValueError, KeyError):
            logger.warning("skipping_malformed_issue", item=item)

    return issues


class BaseAdapter(ABC):
    """Abstract base for all LLM adapters."""

    def __init__(self, config: LocalDuckConfig) -> None:
        self.config = config
        self._categories = config.checks.enabled_categories()

    @property
    def label(self) -> str:
        """Human-readable label for this adapter (shown in CLI output)."""
        return "base"

    @abstractmethod
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt to the LLM and return the raw response text."""
        ...

    async def review(self, diffs: list[FileDiff]) -> list[Issue]:
        """Review a batch of file diffs and return found issues."""
        if not diffs:
            return []

        system = build_system_prompt(self._categories)
        user = build_review_prompt(diffs)

        logger.debug("calling_llm", adapter=self.label, num_diffs=len(diffs))
        raw_response = await self._call_llm(system, user)

        return parse_review_response(raw_response)
