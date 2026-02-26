"""Manual multi-provider adapter — all providers via LiteLLM."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from litellm import acompletion

from localduck.agents.base import BaseAdapter
from localduck.types import ProviderId

if TYPE_CHECKING:
    from localduck.config import LocalDuckConfig

logger = structlog.get_logger()

# Provider → default model mapping
PROVIDER_DEFAULTS: dict[ProviderId, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "xai": "grok-3",
    "gemini": "gemini/gemini-2.0-flash",
    "deepseek": "deepseek/deepseek-chat",
    "mistral": "mistral/mistral-large-latest",
}

# Provider → display name
PROVIDER_NAMES: dict[ProviderId, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "xai": "xAI",
    "gemini": "Google Gemini",
    "deepseek": "DeepSeek",
    "mistral": "Mistral",
}

# Provider → list of available models for setup wizard
PROVIDER_MODELS: dict[ProviderId, list[str]] = {
    "openai": ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"],
    "anthropic": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-haiku-20241022"],
    "xai": ["grok-3", "grok-3-mini"],
    "gemini": ["gemini/gemini-2.0-flash", "gemini/gemini-2.0-pro", "gemini/gemini-1.5-pro"],
    "deepseek": ["deepseek/deepseek-chat", "deepseek/deepseek-reasoner"],
    "mistral": ["mistral/mistral-large-latest", "mistral/codestral-latest"],
}

# Map provider → LiteLLM env variable name for the API key
_API_KEY_ENV_MAP: dict[ProviderId, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}


def _litellm_model_name(provider: ProviderId, model: str) -> str:
    """Return the model identifier LiteLLM expects."""
    # LiteLLM expects provider-prefixed names for some providers
    # If the model already contains a '/', it's already prefixed
    if "/" in model:
        return model
    if provider in ("openai", "anthropic", "xai"):
        return model
    return f"{provider}/{model}"


class ManualAdapter(BaseAdapter):
    """Adapter that uses LiteLLM to call any supported provider."""

    def __init__(self, config: LocalDuckConfig) -> None:
        super().__init__(config)
        if not config.provider:
            raise RuntimeError("Manual mode requires a provider. Run `localduck setup`.")
        self._provider: ProviderId = config.provider
        self._model = config.model or PROVIDER_DEFAULTS[self._provider]
        self._api_key = config.api_key

        # Set the API key for LiteLLM
        if self._api_key:
            import os

            env_var = _API_KEY_ENV_MAP.get(self._provider)
            if env_var:
                os.environ[env_var] = self._api_key

    @property
    def label(self) -> str:
        display = PROVIDER_NAMES.get(self._provider, self._provider)
        return f"{display} ({self._model})"

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        model_name = _litellm_model_name(self._provider, self._model)

        response = await acompletion(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        return response.choices[0].message.content  # type: ignore[union-attr]
