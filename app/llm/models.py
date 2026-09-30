"""Response model returned by app.llm.assistant.answer_question."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None


class AssistantResponse(BaseModel):
    question: str
    answer: str
    tool_calls: list[ToolCallRecord]
