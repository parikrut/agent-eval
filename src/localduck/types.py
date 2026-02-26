"""Core data types for LocalDuck."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class Severity(StrEnum):
    """Issue severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class CheckCategory(StrEnum):
    """Available check categories."""

    CODE_QUALITY = "codeQuality"
    SECURITY = "security"
    CODE_SMELL = "codeSmell"
    LICENSE = "license"
    DOCUMENTATION = "documentation"
    TEST_COVERAGE = "testCoverage"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    LLM_SPECIFIC = "llmSpecific"


AgentMode = Literal["copilot", "manual"]

ProviderId = Literal[
    "openai",
    "anthropic",
    "xai",
    "gemini",
    "deepseek",
    "mistral",
]

BlockOn = Literal["critical", "warning", "all", "none"]

ReportFormat = Literal["html", "markdown"]


@dataclass(frozen=True, slots=True)
class FileDiff:
    """A single file's diff extracted from git."""

    path: str
    diff: str
    is_new: bool = False
    is_deleted: bool = False


@dataclass(frozen=True, slots=True)
class Issue:
    """A single issue found during review."""

    file: str
    line: int | None
    severity: Severity
    category: CheckCategory
    message: str
    suggestion: str = ""


@dataclass(slots=True)
class ScanResult:
    """Complete result of a scan run."""

    issues: list[Issue] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    files_cached: int = 0
    files_deduped: int = 0
    token_usage: int = 0
    cache_hits: int = 0
    skipped_files: list[str] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)

    @property
    def has_warning(self) -> bool:
        return any(i.severity == Severity.WARNING for i in self.issues)

    def should_block(self, block_on: BlockOn) -> bool:
        """Determine if the commit should be blocked based on the block_on setting."""
        match block_on:
            case "none":
                return False
            case "critical":
                return self.has_critical
            case "warning":
                return self.has_critical or self.has_warning
            case "all":
                return len(self.issues) > 0
