"""Lazy OpenAI-compatible LLM client with automatic provider fallback.

Nothing is constructed at import time, so app.llm.assistant can be imported
and unit tested without any API key in the environment.

Providers are plain OpenAI-compatible endpoints, configured via env:

  LLM_BASE_URL / LLM_API_KEY / LLM_MODEL                 primary (default: Groq free tier)
  LLM_FALLBACK_BASE_URL / LLM_FALLBACK_API_KEY / LLM_FALLBACK_MODEL   optional second provider

If the primary raises a rate-limit, connection, timeout or server error, the
same request is retried once against the fallback.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import openai
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"  # Groq free tier, supports tool calling

_FALLBACK_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
    openai.AuthenticationError,
    openai.NotFoundError,
    openai.BadRequestError,  # e.g. malformed tool call from a flaky model
)


@dataclass
class Provider:
    name: str
    client: OpenAI
    model: str


_providers: list[Provider] | None = None
_env_loaded = False


def _build_providers() -> list[Provider]:
    providers: list[Provider] = []

    api_key = os.environ.get("LLM_API_KEY")
    if api_key:
        providers.append(
            Provider(
                "primary",
                OpenAI(
                    base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
                    api_key=api_key,
                    max_retries=1,
                    timeout=30,
                ),
                os.environ.get("LLM_MODEL", DEFAULT_MODEL),
            )
        )

    fb_url = os.environ.get("LLM_FALLBACK_BASE_URL")
    fb_model = os.environ.get("LLM_FALLBACK_MODEL")
    if fb_url and fb_model:
        # Local Ollama ignores the key but the SDK requires a non-empty one.
        fb_key = os.environ.get("LLM_FALLBACK_API_KEY") or "not-needed"
        providers.append(
            Provider("fallback", OpenAI(base_url=fb_url, api_key=fb_key, max_retries=1, timeout=60), fb_model)
        )

    if not providers:
        raise RuntimeError(
            "LLM_API_KEY is not set. Copy .env.example to .env and add a free "
            "Groq key (https://console.groq.com/keys), or configure LLM_FALLBACK_*."
        )
    return providers


def get_providers() -> list[Provider]:
    global _providers, _env_loaded
    if not _env_loaded:
        load_dotenv()
        _env_loaded = True
    if _providers is None:
        _providers = _build_providers()
    return _providers


def create_chat_completion(**kwargs):
    """Call chat.completions.create on the first working provider.

    `model` is chosen per provider; do not pass it.
    """
    providers = get_providers()
    last_exc: Exception | None = None
    for provider in providers:
        try:
            return provider.client.chat.completions.create(model=provider.model, **kwargs)
        except _FALLBACK_ERRORS as exc:
            logger.warning("LLM provider %s failed (%s); trying next", provider.name, type(exc).__name__)
            last_exc = exc
    raise RuntimeError(f"All LLM providers failed: {type(last_exc).__name__}") from last_exc
