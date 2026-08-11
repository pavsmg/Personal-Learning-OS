import json
import sys
from dataclasses import dataclass
from typing import Any, Callable

from learning_os.conversation.llm_client import LLMReply, chat_completion, to_openai_tools
from learning_os.conversation.prompt import build_system_prompt
from learning_os.sessions import create_session, finish_session, record_turn, summarize_session
from learning_os.sessions.models import SessionSummary
from learning_os.tools_interface import call_tool

CONVERSATION_TOOLS = ["search_notes", "get_note", "related_notes", "save_mistake", "get_recent_mistakes"]
END_SESSION_NUDGE = "[The learner wants to end the session now.]"
QUIT_COMMANDS = {"quit", "exit", "done"}

ChatFn = Callable[[list[dict[str, Any]], list[dict[str, Any]]], LLMReply]


@dataclass
class ConversationState:
    session_id: str
    messages: list[dict[str, Any]]


def _get_assistant_reply(messages: list[dict[str, Any]], chat_fn: ChatFn = chat_completion) -> str:
    tools = to_openai_tools(CONVERSATION_TOOLS)
    while True:
        reply = chat_fn(messages, tools)
        if not reply.tool_calls:
            messages.append({"role": "assistant", "content": reply.content})
            return reply.content or ""

        messages.append(
            {
                "role": "assistant",
                "content": reply.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": _dumps(call.arguments)},
                    }
                    for call in reply.tool_calls
                ],
            }
        )
        for call in reply.tool_calls:
            try:
                result = call_tool(call.name, **call.arguments)
                content = _dumps(_serialize(result))
            except Exception as exc:  # noqa: BLE001 — feed the error back to the model, don't crash the loop
                content = _dumps({"error": str(exc)})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})


def _serialize(value: Any) -> Any:
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _dumps(value: Any) -> str:
    return json.dumps(value)


def start_session(topic: str | None = None, chat_fn: ChatFn = chat_completion) -> tuple[ConversationState, str]:
    plan = create_session(topic)
    messages = [{"role": "system", "content": build_system_prompt(plan)}]
    opening = _get_assistant_reply(messages, chat_fn)
    record_turn(plan.session_id, "assistant", opening)
    return ConversationState(session_id=plan.session_id, messages=messages), opening


def send_message(state: ConversationState, user_text: str, chat_fn: ChatFn = chat_completion) -> str:
    state.messages.append({"role": "user", "content": user_text})
    record_turn(state.session_id, "user", user_text)
    reply = _get_assistant_reply(state.messages, chat_fn)
    record_turn(state.session_id, "assistant", reply)
    return reply


def end_session(state: ConversationState, chat_fn: ChatFn = chat_completion) -> tuple[str, SessionSummary]:
    state.messages.append({"role": "user", "content": END_SESSION_NUDGE})
    closing = _get_assistant_reply(state.messages, chat_fn)
    record_turn(state.session_id, "assistant", closing)
    finish_session(state.session_id)
    return closing, summarize_session(state.session_id)


def run() -> None:
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = input("What do you want to study today? (leave blank to let it pick) ").strip() or None
    state, opening = start_session(topic)
    print(f"\n{opening}\n")

    while True:
        user_text = input("> ").strip()
        if user_text.lower() in QUIT_COMMANDS:
            closing, summary = end_session(state)
            print(f"\n{closing}\n")
            print(f"--- {summary.summary} ---")
            break
        reply = send_message(state, user_text)
        print(f"\n{reply}\n")


if __name__ == "__main__":
    run()
