"""Configuration loading and validation for LocalDuck."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from localduck.types import (
    AgentMode,
    BlockOn,
    CheckCategory,
    ProviderId,
    ReportFormat,
)

CONFIG_FILENAME = ".localduckrc"


class ChecksConfig(BaseModel):
    """Toggle individual check categories."""

    code_quality: bool = Field(True, alias="codeQuality")
    security: bool = Field(True, alias="security")
    code_smell: bool = Field(True, alias="codeSmell")
    license: bool = Field(False, alias="license")
    documentation: bool = Field(True, alias="documentation")
    test_coverage: bool = Field(False, alias="testCoverage")
    performance: bool = Field(False, alias="performance")
    accessibility: bool = Field(False, alias="accessibility")
    llm_specific: bool = Field(False, alias="llmSpecific")

    model_config = {"populate_by_name": True}

    def enabled_categories(self) -> list[CheckCategory]:
        """Return the list of enabled check categories."""
        mapping: dict[str, CheckCategory] = {
            "code_quality": CheckCategory.CODE_QUALITY,
            "security": CheckCategory.SECURITY,
            "code_smell": CheckCategory.CODE_SMELL,
            "license": CheckCategory.LICENSE,
            "documentation": CheckCategory.DOCUMENTATION,
            "test_coverage": CheckCategory.TEST_COVERAGE,
            "performance": CheckCategory.PERFORMANCE,
            "accessibility": CheckCategory.ACCESSIBILITY,
            "llm_specific": CheckCategory.LLM_SPECIFIC,
        }
        return [cat for attr, cat in mapping.items() if getattr(self, attr)]


class LocalDuckConfig(BaseModel):
    """Root configuration model — maps 1:1 to .localduckrc JSON."""

    agent: AgentMode = "copilot"
    provider: ProviderId | None = None
    model: str | None = None
    api_key: str | None = Field(None, alias="apiKey")
    block_on: BlockOn = Field("critical", alias="blockOn")
    token_budget: int = Field(50_000, alias="tokenBudget")
    cache_threshold: float = Field(0.92, alias="cacheThreshold")
    max_concurrent: int = Field(3, alias="maxConcurrent")
    checks: ChecksConfig = Field(default_factory=ChecksConfig)
    report_format: ReportFormat = Field("html", alias="reportFormat")
    report_dir: str = Field(".localduck/reports", alias="reportDir")

    model_config = {"populate_by_name": True}

    def to_rc_dict(self) -> dict[str, Any]:
        """Serialize to the JSON structure used in .localduckrc."""
        data: dict[str, Any] = {"agent": self.agent}
        if self.provider is not None:
            data["provider"] = self.provider
        if self.model is not None:
            data["model"] = self.model
        if self.api_key is not None:
            data["apiKey"] = self.api_key
        data["blockOn"] = self.block_on
        data["tokenBudget"] = self.token_budget
        data["cacheThreshold"] = self.cache_threshold
        data["maxConcurrent"] = self.max_concurrent
        data["checks"] = self.checks.model_dump(by_alias=True)
        data["reportFormat"] = self.report_format
        data["reportDir"] = self.report_dir
        return data


def find_config_file(start: Path | None = None) -> Path | None:
    """Walk up from `start` (default: cwd) to find .localduckrc."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path | None = None) -> LocalDuckConfig:
    """Load and validate config from .localduckrc, falling back to defaults."""
    config_path = path or find_config_file()
    if config_path is None or not config_path.is_file():
        return LocalDuckConfig()

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return LocalDuckConfig.model_validate(raw)


def save_config(config: LocalDuckConfig, directory: Path | None = None) -> Path:
    """Write config to .localduckrc in the given directory (default: cwd)."""
    target = (directory or Path.cwd()) / CONFIG_FILENAME
    target.write_text(
        json.dumps(config.to_rc_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return target
