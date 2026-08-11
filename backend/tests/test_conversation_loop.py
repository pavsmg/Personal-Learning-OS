import json

from learning_os.llm_client import LLMReply, ToolCallRequest
from learning_os.conversation.loop import END_SESSION_NUDGE, end_session, send_message, start_session


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")


class ScriptedChat:
    """Fake chat_fn: returns each LLMReply in order, one per call. No network."""

    def __init__(self, replies: list[LLMReply]):
        self._replies = list(replies)
        self.calls: list[list[dict]] = []

    def __call__(self, messages, tools):
        self.calls.append([dict(m) for m in messages])
        return self._replies.pop(0)


def test_start_session_returns_opening_and_seeds_system_prompt(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    chat = ScriptedChat([LLMReply(content="Hi! Ready to talk gradient descent?", tool_calls=[])])

    state, opening = start_session("gradient descent", chat_fn=chat)

    assert opening == "Hi! Ready to talk gradient descent?"
    assert state.messages[0]["role"] == "system"
    assert "Gradient descent" in state.messages[0]["content"]


def test_send_message_resolves_tool_call_before_returning_reply(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "Gradient descent.md": "core optimization concept, linked to [[Optimizer]].",
            "Optimizer.md": "general term for optimization algorithms.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    chat = ScriptedChat(
        [
            LLMReply(content="Opening.", tool_calls=[]),
            LLMReply(
                content=None,
                tool_calls=[ToolCallRequest(id="call_1", name="search_notes", arguments={"query": "optimizer"})],
            ),
            LLMReply(content="Optimizer is the general term — can you explain gradient descent specifically?", tool_calls=[]),
        ]
    )
    state, _ = start_session("gradient descent", chat_fn=chat)

    reply = send_message(state, "What's an optimizer?", chat_fn=chat)

    assert reply == "Optimizer is the general term — can you explain gradient descent specifically?"
    tool_messages = [m for m in state.messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    result = json.loads(tool_messages[0]["content"])
    assert result[0]["title"] == "Optimizer"


def test_send_message_resolves_save_mistake_tool_call(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "---\ndomain: classical-ml\n---\ncore optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    chat = ScriptedChat(
        [
            LLMReply(content="Opening.", tool_calls=[]),
            LLMReply(
                content=None,
                tool_calls=[
                    ToolCallRequest(
                        id="call_1",
                        name="save_mistake",
                        arguments={
                            "concept": "Gradient descent",
                            "explanation": "thought it maximizes loss",
                            "category": "conceptual",
                            "severity": "minor",
                            "confidence": 0.7,
                            "domain": "classical-ml",
                        },
                    )
                ],
            ),
            LLMReply(content="Got it, noted — let's try again.", tool_calls=[]),
        ]
    )
    state, _ = start_session("gradient descent", chat_fn=chat)

    reply = send_message(state, "Gradient descent maximizes the loss, right?", chat_fn=chat)

    assert reply == "Got it, noted — let's try again."
    from learning_os.mistakes.service import get_recent_mistakes

    saved = get_recent_mistakes(domain="classical-ml")
    assert len(saved) == 1
    assert saved[0].concept == "Gradient descent"


def test_end_session_sends_nudge_then_finishes_and_summarizes(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    chat = ScriptedChat(
        [
            LLMReply(content="Opening.", tool_calls=[]),
            LLMReply(content="Good luck with gradient descent going forward!", tool_calls=[]),
        ]
    )
    state, _ = start_session("gradient descent", chat_fn=chat)

    closing, summary = end_session(state, chat_fn=chat)

    assert closing == "Good luck with gradient descent going forward!"
    assert summary.session_id == state.session_id
    last_call_messages = chat.calls[-1]
    assert last_call_messages[-1] == {"role": "user", "content": END_SESSION_NUDGE}
