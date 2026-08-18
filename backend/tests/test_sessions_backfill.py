from learning_os.llm_client import LLMReply, ToolCallRequest
from learning_os.mistakes import store
from learning_os.sessions.backfill import _parse_session_start, backfill_session


class FakeChat:
    def __init__(self, reply: LLMReply):
        self._reply = reply
        self.calls: list[dict] = []

    def __call__(self, messages, tools, tool_choice=None):
        self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice})
        return self._reply


def grading_reply(grades: list[dict]) -> LLMReply:
    return LLMReply(
        content=None,
        tool_calls=[ToolCallRequest(id="call_1", name="record_session_grades", arguments={"grades": grades})],
    )


def test_parse_session_start_extracts_domain_and_concepts():
    line = "[05:57:03] SESSION START domain='physics' objective='Review Physics and related concepts' concepts=['Physics', 'Electromagnetism']"

    parsed = _parse_session_start(line)

    assert parsed == ("physics", ["Physics", "Electromagnetism"])


def test_parse_session_start_returns_none_for_unrelated_line():
    assert _parse_session_start("[05:57:03] ASSISTANT: hello") is None


def test_backfill_session_writes_evidence_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    from learning_os import session_log as session_log_module

    monkeypatch.setattr(session_log_module, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr("learning_os.sessions.backfill.LOG_DIR", tmp_path / "logs")

    log_path = tmp_path / "logs" / "session-1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "[05:57:03] SESSION START domain='physics' objective='Review Physics' concepts=['Electromagnetism']\n"
        "[05:57:10] ASSISTANT: Correct.\n",
        encoding="utf-8",
    )
    chat = FakeChat(grading_reply([{"concept": "Electromagnetism", "outcome": "correct", "quality": 0.9, "rationale": "x"}]))

    monkeypatch.setattr("learning_os.sessions.backfill.chat_completion", chat)
    result = backfill_session(log_path)

    assert "graded 1 concepts" in result
    assert len(store.query_evidence(session_id="session-1")) == 1

    # Second call must skip -- already graded.
    second_result = backfill_session(log_path)
    assert "already graded, skipped" in second_result
    assert len(chat.calls) == 1


def test_backfill_session_skips_log_without_session_start(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    from learning_os import session_log as session_log_module

    monkeypatch.setattr(session_log_module, "LOG_DIR", tmp_path / "logs")

    log_path = tmp_path / "logs" / "session-2.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("[05:57:03] ASSISTANT: no session start line here\n", encoding="utf-8")

    result = backfill_session(log_path)

    assert "no SESSION START line found, skipped" in result
    assert store.query_evidence(session_id="session-2") == []
