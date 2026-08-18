import json

from learning_os.llm_client import LLMReply, ToolCallRequest
from learning_os.conversation.loop import END_SESSION_NUDGE, end_session, send_message, start_session


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")


class ScriptedChat:
    """Fake chat_fn: returns each LLMReply in order, one per call. No network.
    Accepts tool_choice (unused) to match chat_completion's real signature --
    end_session forwards this same chat_fn into finish_session's grading
    pass, which always calls with a forced tool_choice."""

    def __init__(self, replies: list[LLMReply]):
        self._replies = list(replies)
        self.calls: list[list[dict]] = []

    def __call__(self, messages, tools, tool_choice=None):
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
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    chat = ScriptedChat(
        [
            LLMReply(content="Opening.", tool_calls=[]),
            LLMReply(content="Good luck with gradient descent going forward!", tool_calls=[]),
            LLMReply(
                content=None,
                tool_calls=[
                    ToolCallRequest(
                        id="grade_1",
                        name="record_session_grades",
                        arguments={
                            "grades": [
                                {
                                    "concept": "Gradient descent",
                                    "outcome": "not_reached",
                                    "quality": 0.9,
                                    "rationale": "never actually quizzed in this exchange",
                                }
                            ]
                        },
                    )
                ],
            ),
        ]
    )
    state, _ = start_session("gradient descent", chat_fn=chat)

    closing, summary = end_session(state, chat_fn=chat)

    assert closing == "Good luck with gradient descent going forward!"
    assert summary.session_id == state.session_id
    last_call_messages = chat.calls[-2]
    assert last_call_messages[-1] == {"role": "user", "content": END_SESSION_NUDGE}


def test_text_session_writes_a_transcript_with_tool_calls(tmp_path, monkeypatch):
    """Parity with the voice loop: a text session has to leave the same kind
    of readable record, or decisions.md #44's end-of-session grading has
    nothing to read for half the sessions."""
    from learning_os import session_log as session_log_module

    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(session_log_module, "LOG_DIR", tmp_path / "logs")
    chat = ScriptedChat(
        [
            LLMReply(
                content=None,
                tool_calls=[ToolCallRequest(id="c1", name="search_notes", arguments={"query": "gradient descent"})],
            ),
            LLMReply(content="How would you explain gradient descent?", tool_calls=[]),
            LLMReply(content="Close, but not quite.", tool_calls=[]),
            LLMReply(content="Good work today.", tool_calls=[]),
            LLMReply(
                content=None,
                tool_calls=[
                    ToolCallRequest(
                        id="grade_1",
                        name="record_session_grades",
                        arguments={
                            "grades": [
                                {
                                    "concept": "Gradient descent",
                                    "outcome": "incorrect",
                                    "quality": 0.9,
                                    "rationale": "learner's explanation was corrected mid-session",
                                }
                            ]
                        },
                    )
                ],
            ),
        ]
    )

    state, _ = start_session("gradient descent", chat_fn=chat)
    send_message(state, "It goes downhill.", chat_fn=chat)
    end_session(state, chat_fn=chat)

    transcript = (tmp_path / "logs" / f"{state.session_id}.log").read_text(encoding="utf-8")
    assert "SESSION START" in transcript
    assert "TOOL CALL: search_notes" in transcript
    assert "USER: It goes downhill." in transcript
    assert "ASSISTANT: How would you explain gradient descent?" in transcript
    assert "SUMMARY:" in transcript
    assert transcript.strip().endswith("SESSION END")
    # decisions.md #44: the grading pass's rationale is sampleable from the
    # same log, not just the discrete outcome.
    assert "GRADE: Gradient descent -> incorrect" in transcript


def test_tool_calls_are_logged_even_without_debug(tmp_path, monkeypatch):
    """--debug controls the terminal, not the record."""
    from learning_os import session_log as session_log_module

    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(session_log_module, "LOG_DIR", tmp_path / "logs")
    chat = ScriptedChat(
        [
            LLMReply(
                content=None,
                tool_calls=[ToolCallRequest(id="c1", name="search_notes", arguments={"query": "gradient descent"})],
            ),
            LLMReply(content="Opening.", tool_calls=[]),
        ]
    )

    state, _ = start_session("gradient descent", chat_fn=chat, debug=False)

    transcript = (tmp_path / "logs" / f"{state.session_id}.log").read_text(encoding="utf-8")
    assert "TOOL CALL: search_notes" in transcript
