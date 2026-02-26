"""Adapter factory — create the right adapter based on config."""

from __future__ import annotations

from localduck.agents.base import BaseAdapter
from localduck.agents.copilot import CopilotAdapter
from localduck.agents.manual import ManualAdapter
from localduck.config import LocalDuckConfig


def create_adapter(config: LocalDuckConfig) -> BaseAdapter:
    """Instantiate the appropriate LLM adapter for the given config."""
    match config.agent:
        case "copilot":
            return CopilotAdapter(config)
        case "manual":
            return ManualAdapter(config)
        case _:
            raise ValueError(f"Unknown agent mode: {config.agent}")
