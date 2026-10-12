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
                json.dumps(record.result)
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
