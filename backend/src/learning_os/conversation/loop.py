import argparse
from dataclasses import dataclass, field
from itertools import count
from typing import Any, Callable, Iterator

from learning_os.conversation.prompt import END_SESSION_NUDGE, TUTORING_TOOLS, build_system_prompt
from learning_os.debug_output import print_tool_call
from learning_os.llm_client import LLMReply, chat_completion
from learning_os.serialization import serialize_for_json, to_json
from learning_os.session_log import SessionLog
from learning_os.sessions import create_session, finish_session, record_turn, summarize_session
from learning_os.sessions.models import SessionSummary
from learning_os.tools_interface import TOOLS, call_tool

QUIT_COMMANDS = {"quit", "exit", "done"}

ChatFn = Callable[[list[dict[str, Any]], list[dict[str, Any]]], LLMReply]


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


@dataclass
class ConversationState:
    session_id: str
    messages: list[dict[str, Any]]
    debug: bool = False
    call_counter: Iterator[int] = field(default_factory=lambda: count(1))
    log: SessionLog | None = None


def _get_assistant_reply(
    messages: list[dict[str, Any]],
    chat_fn: ChatFn = chat_completion,
    debug: bool = False,
    call_counter: Iterator[int] | None = None,
    log: SessionLog | None = None,
) -> str:
    tools = to_openai_tools(TUTORING_TOOLS)
    counter = call_counter if call_counter is not None else count(1)
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
                        "function": {"name": call.name, "arguments": to_json(call.arguments)},
                    }
                    for call in reply.tool_calls
                ],
            }
        )
        for call in reply.tool_calls:
            try:
                result = call_tool(call.name, **call.arguments)
                content = to_json(serialize_for_json(result))
            except Exception as exc:  # noqa: BLE001 — feed the error back to the model, don't crash the loop
                content = to_json({"error": str(exc)})
            if debug:
                print_tool_call(next(counter), call.name, call.arguments, content)
            if log is not None:
                # Logged regardless of --debug: the transcript is the record,
                # --debug is only about what the terminal shows right now.
                log.write(f"TOOL CALL: {call.name}({call.arguments}) -> {content}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})


def start_session(
    topic: str | None = None, chat_fn: ChatFn = chat_completion, debug: bool = False
) -> tuple[ConversationState, str]:
    plan = create_session(topic)
    messages = [{"role": "system", "content": build_system_prompt(plan)}]
    call_counter = count(1)
    log = SessionLog(plan.session_id)
    log.write(f"SESSION START domain={plan.domain!r} objective={plan.objective!r} concepts={plan.concepts}")

    opening = _get_assistant_reply(messages, chat_fn, debug=debug, call_counter=call_counter, log=log)
    record_turn(plan.session_id, "assistant", opening)
    log.write(f"ASSISTANT: {opening}")

    state = ConversationState(
        session_id=plan.session_id, messages=messages, debug=debug, call_counter=call_counter, log=log
    )
    return state, opening


def send_message(state: ConversationState, user_text: str, chat_fn: ChatFn = chat_completion) -> str:
    state.messages.append({"role": "user", "content": user_text})
    record_turn(state.session_id, "user", user_text)
    if state.log is not None:
        state.log.write(f"USER: {user_text}")

    reply = _get_assistant_reply(
        state.messages, chat_fn, debug=state.debug, call_counter=state.call_counter, log=state.log
    )
    record_turn(state.session_id, "assistant", reply)
    if state.log is not None:
        state.log.write(f"ASSISTANT: {reply}")
    return reply


def end_session(state: ConversationState, chat_fn: ChatFn = chat_completion) -> tuple[str, SessionSummary]:
    state.messages.append({"role": "user", "content": END_SESSION_NUDGE})
    closing = _get_assistant_reply(
        state.messages, chat_fn, debug=state.debug, call_counter=state.call_counter, log=state.log
    )
    record_turn(state.session_id, "assistant", closing)
    finish_session(state.session_id, _chat_fn=chat_fn)
    summary = summarize_session(state.session_id)

    if state.log is not None:
        state.log.write(f"ASSISTANT: {closing}")
        state.log.write(f"SUMMARY: {summary.summary}")
        state.log.write("SESSION END")
        state.log.close()
    return closing, summary


def run() -> None:
    parser = argparse.ArgumentParser(description="Personal Learning OS — text conversation")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Print each tool call (name, arguments, and result) as it happens, for inspection/testing.",
    )
    parser.add_argument(
        "topic", nargs="*", help="Topic to study (omit to let the system pick automatically)."
    )
    args = parser.parse_args()

    topic = " ".join(args.topic) if args.topic else None
    if topic is None:
        topic = input("What do you want to study today? (leave blank to let it pick) ").strip() or None

    state, opening = start_session(topic, debug=args.debug)
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
