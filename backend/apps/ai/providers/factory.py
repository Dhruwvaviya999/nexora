"""
LLM provider factory.

Resolves the provider for a workspace: per-workspace ``AISettings`` win, falling
back to the project-wide defaults in ``settings.AI``. API keys come from the
workspace settings (decrypted) or the env-level fallback key for that provider.
"""

from __future__ import annotations

from django.conf import settings

from apps.ai.providers.base import BaseLLMProvider, ProviderError
from apps.ai.providers.gemini import GeminiProvider
from apps.ai.providers.ollama import OllamaProvider
from apps.ai.providers.openai import OpenAIProvider
from apps.ai.services import crypto

_PROVIDERS: dict[str, type[BaseLLMProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}

# Env-level fallback API keys per provider (per-workspace keys override these).
_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "ollama": "",  # local, no key
}


def get_llm_settings(workspace) -> dict:
    """Effective LLM config for ``workspace`` (settings row merged over defaults)."""
    ai = settings.AI
    resolved = {
        "provider": ai["DEFAULT_LLM_PROVIDER"],
        "model": ai["DEFAULT_CHAT_MODEL"],
        "temperature": ai["DEFAULT_TEMPERATURE"],
        "max_tokens": ai["DEFAULT_MAX_TOKENS"],
        "api_key": "",
        "is_enabled": True,
    }

    row = getattr(workspace, "ai_settings", None)
    if row is not None:
        resolved.update(
            provider=row.provider or resolved["provider"],
            model=row.chat_model or resolved["model"],
            temperature=row.temperature,
            max_tokens=row.max_tokens,
            is_enabled=row.is_enabled,
            api_key=crypto.decrypt(row.api_key_encrypted),
        )

    # Fall back to an env-level key for the chosen provider when none is set.
    if not resolved["api_key"]:
        env_key = _ENV_KEYS.get(resolved["provider"], "")
        if env_key:
            resolved["api_key"] = settings.AI.get(env_key, "")

    return resolved


def get_llm_provider(workspace) -> BaseLLMProvider:
    cfg = get_llm_settings(workspace)
    if not cfg["is_enabled"]:
        raise ProviderError("AI is disabled for this workspace.")

    provider_cls = _PROVIDERS.get(cfg["provider"])
    if provider_cls is None:
        raise ProviderError(f"Unknown LLM provider: {cfg['provider']!r}")

    return provider_cls(model=cfg["model"], api_key=cfg["api_key"])
