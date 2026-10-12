"""Empty-completion handling in app.llm.assistant (no network)."""

from types import SimpleNamespace

from app.llm import assistant


def _resp(content=None, tool_calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))])


def _tool_call():
    fn = SimpleNamespace(name="get_sales_summary", arguments='{"start_date":"2024-04-01","end_date":"2024-04-30"}')
    tc = SimpleNamespace(id="1", function=fn)
    tc.model_dump = lambda: {"id": "1", "type": "function", "function": {"name": fn.name, "arguments": fn.arguments}}
    return tc


def _patch(monkeypatch, replies, calls):
    it = iter(replies)

    def fake(**kw):
        calls.append(kw)
        return next(it)

    monkeypatch.setattr(assistant, "create_chat_completion", fake)
    monkeypatch.setattr(
        assistant, "_execute_tool",
        lambda name, args: assistant.ToolCallRecord(tool_name=name, arguments=args, result={"total_revenue": 5}),
    )


def test_empty_final_content_is_retried_with_nudge(monkeypatch):
    calls = []
    _patch(monkeypatch, [_resp(tool_calls=[_tool_call()]), _resp(""), _resp("Revenue was $5.")], calls)
    out = assistant.answer_question("q")
    assert out.answer == "Revenue was $5."
    assert calls[-1]["messages"][-1]["content"] == assistant._NUDGE


def test_falls_back_to_fallback_model_then_deterministic_summary(monkeypatch):
    calls = []
    _patch(monkeypatch, [_resp(tool_calls=[_tool_call()]), _resp("  "), _resp(None), _resp("")], calls)
    out = assistant.answer_question("q")
    assert calls[-1].get("prefer_fallback") is True
    assert "get_sales_summary" in out.answer and "total_revenue" in out.answer


def test_empty_without_tools_never_returns_blank(monkeypatch):
    _patch(monkeypatch, [_resp(""), _resp(""), _resp("")], [])
    assert assistant.answer_question("q").answer.strip()
