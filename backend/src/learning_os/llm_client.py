import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from openai import OpenAI

from learning_os.config import get_settings


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


def embed_texts(texts: list[str]) -> list[list[float]]:
    response = _get_client().embeddings.create(model=get_settings().openai_embedding_model, input=texts)
    return [item.embedding for item in response.data]


def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    tool_choice: dict[str, Any] | None = None,
) -> LLMReply:
    kwargs: dict[str, Any] = {"model": get_settings().openai_model, "messages": messages, "tools": tools}
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    response = _get_client().chat.completions.create(**kwargs)
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
