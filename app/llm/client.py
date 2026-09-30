"""Lazy OpenAI client — never constructed at import time.

Lets app.llm.assistant (and anything that imports it) be imported and unit
tested without OPENAI_API_KEY present in the environment.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

_client: OpenAI | None = None
_env_loaded = False

DEFAULT_MODEL = "gpt-4o-mini"


def get_openai_client() -> OpenAI:
    global _client, _env_loaded
    if not _env_loaded:
        load_dotenv()
        _env_loaded = True
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        _client = OpenAI(api_key=api_key)
    return _client
