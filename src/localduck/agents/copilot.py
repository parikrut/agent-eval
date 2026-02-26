"""GitHub Copilot adapter — uses the GitHub Models API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import structlog

from localduck.agents.base import BaseAdapter
from localduck.agents.detect import detect_copilot

if TYPE_CHECKING:
    from localduck.config import LocalDuckConfig

logger = structlog.get_logger()

GITHUB_MODELS_URL = "https://models.inference.ai.azure.com/chat/completions"
DEFAULT_MODEL = "gpt-4o"


class CopilotAdapter(BaseAdapter):
    """Adapter that calls the GitHub Models API using a gh CLI token."""

    def __init__(self, config: LocalDuckConfig) -> None:
        super().__init__(config)
        status = detect_copilot()
        if not status.available or not status.token:
            raise RuntimeError(
                f"Copilot not available: {status.reason}. "
                "Run `gh auth login` or set GITHUB_TOKEN."
            )
        self._token = status.token
        self._model = config.model or DEFAULT_MODEL

    @property
    def label(self) -> str:
        return f"Copilot ({self._model})"

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                GITHUB_MODELS_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]
