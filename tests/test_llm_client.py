"""Provider fallback behaviour (no network; fake clients)."""

from types import SimpleNamespace

import httpx
import openai
import pytest

from app.llm import client as llm_client


def _provider(name, behaviour):
    create = lambda **kw: behaviour(kw)  # noqa: E731
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return llm_client.Provider(name, fake, f"{name}-model")


def _rate_limit(_):
    req = httpx.Request("POST", "http://x")
    raise openai.RateLimitError("slow down", response=httpx.Response(429, request=req), body=None)


def test_falls_back_on_rate_limit(monkeypatch):
    ok = _provider("fallback", lambda kw: kw["model"])
    monkeypatch.setattr(llm_client, "_providers", [_provider("primary", _rate_limit), ok])
    assert llm_client.create_chat_completion(messages=[]) == "fallback-model"


def test_raises_when_all_providers_fail(monkeypatch):
    monkeypatch.setattr(llm_client, "_providers", [_provider("primary", _rate_limit)])
    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        llm_client.create_chat_completion(messages=[])
