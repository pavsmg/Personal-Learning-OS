import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from openai import OpenAI

from learning_os.config import get_settings
from learning_os.tools_interface import TOOLS


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMReply:
    content: str | None
    tool_calls: list[ToolCallRequest]


@lru_cache
def _get_client() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key)


def to_openai_tools(tool_names: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": TOOLS[name].description,
                "parameters": TOOLS[name].parameters_schema,
            },
        }
        for name in tool_names
    ]


def chat_completion(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMReply:
    response = _get_client().chat.completions.create(
        model=get_settings().openai_model,
        messages=messages,
        tools=tools,
    )
    message = response.choices[0].message
    tool_calls = [
        ToolCallRequest(
            id=call.id,
            name=call.function.name,
            arguments=json.loads(call.function.arguments),
        )
        for call in (message.tool_calls or [])
    ]
    return LLMReply(content=message.content, tool_calls=tool_calls)
