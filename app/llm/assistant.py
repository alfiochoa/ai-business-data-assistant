"""LLM tool-calling orchestration.

Flow: user question -> LLM picks a tool (or several, across turns) -> we
execute the *real* Python function from app.tools.registry with validated
parameters -> the structured result goes back to the model -> the model
produces a natural-language explanation, which we return alongside every
tool call actually made (name, arguments, and result/error) so a caller can
verify the answer is grounded in real data.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from app.llm.client import create_chat_completion
from app.llm.models import AssistantResponse, ToolCallRecord
from app.llm.schemas import TOOL_SCHEMAS
from app.llm.system_prompt import SYSTEM_PROMPT
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.registry import TOOL_REGISTRY

MAX_TOOL_ROUNDS = 4


def _execute_tool(tool_name: str, arguments: dict) -> ToolCallRecord:
    func = TOOL_REGISTRY.get(tool_name)
    if func is None:
        return ToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            error=f"Unknown tool {tool_name!r}. No such business capability exists.",
        )
    try:
        result = func(**arguments)
    except ToolValidationError as exc:
        return ToolCallRecord(tool_name=tool_name, arguments=arguments, error=f"Invalid parameters: {exc}")
    except ToolExecutionError as exc:
        return ToolCallRecord(tool_name=tool_name, arguments=arguments, error=f"Tool failed: {exc}")

    result_dict = result.model_dump(mode="json") if isinstance(result, BaseModel) else result
    return ToolCallRecord(tool_name=tool_name, arguments=arguments, result=result_dict)


_MAX_EVENTS_FOR_LLM = 15
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _compact_for_llm(result: dict) -> dict:
    """Shrink long event lists so a single tool result can't blow the model's token limit.

    Counts are exact; only the most severe events are listed individually.
    """
    events = result.get("events")
    if not isinstance(events, list) or len(events) <= _MAX_EVENTS_FOR_LLM:
        return result
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for e in events:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
        by_severity[e["severity"]] = by_severity.get(e["severity"], 0) + 1
    top = sorted(events, key=lambda e: (_SEVERITY_RANK.get(e["severity"], 9), e["event_date"]))
    return {
        **{k: v for k, v in result.items() if k != "events"},
        "total_events": len(events),
        "counts_by_type": by_type,
        "counts_by_severity": by_severity,
        "most_severe_events_sample": top[:_MAX_EVENTS_FOR_LLM],
    }


def answer_question(user_question: str) -> AssistantResponse:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]
    tool_call_records: list[ToolCallRecord] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = create_chat_completion(
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return AssistantResponse(
                question=user_question,
                answer=message.content or "",
                tool_calls=tool_call_records,
            )

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            }
        )

        for tool_call in message.tool_calls:
            try:
                arguments = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}

            record = _execute_tool(tool_call.function.name, arguments)
            tool_call_records.append(record)

            tool_content = (
                json.dumps(_compact_for_llm(record.result))
                if record.error is None
                else json.dumps({"error": record.error})
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_content,
                }
            )

    # Exceeded MAX_TOOL_ROUNDS without a final answer — ask once more without tools
    # so the model is forced to summarize what it has rather than loop forever.
    response = create_chat_completion(messages=messages)
    return AssistantResponse(
        question=user_question,
        answer=response.choices[0].message.content or "",
        tool_calls=tool_call_records,
    )
