from learning_os.llm_client import LLMReply, ToolCallRequest
from learning_os.session_log import SessionLog
from learning_os.sessions.grading import grade_session


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


def test_grade_session_prompt_warns_about_async_transcription_ordering():
    """decisions.md #61: a real voice session log showed a USER line
    appearing after the ASSISTANT reply it was actually answering, since
    transcription completes asynchronously. The grader needs to know this
    isn't necessarily out-of-order discussion."""
    from learning_os.sessions.grading_prompt import build_grading_prompt

    prompt = build_grading_prompt("physics", ["Electromagnetism"], "...")

    assert "asynchronously" in prompt


def test_grade_session_forces_the_grading_tool_choice():
    chat = FakeChat(grading_reply([{"concept": "Gradient descent", "outcome": "correct", "quality": 0.9, "rationale": "x"}]))

    grade_session("session-1", "classical-ml", ["Gradient descent"], "USER: ...", _chat_fn=chat)

    assert chat.calls[0]["tool_choice"] == {"type": "function", "function": {"name": "record_session_grades"}}
    assert chat.calls[0]["tools"][0]["function"]["name"] == "record_session_grades"


def test_grade_session_prompt_includes_domain_concepts_and_transcript():
    chat = FakeChat(grading_reply([{"concept": "Gradient descent", "outcome": "correct", "quality": 0.9, "rationale": "x"}]))

    grade_session("session-1", "classical-ml", ["Gradient descent"], "USER: mixed up the sign", _chat_fn=chat)

    prompt = chat.calls[0]["messages"][0]["content"]
    assert "classical-ml" in prompt
    assert "Gradient descent" in prompt
    assert "mixed up the sign" in prompt


def test_grade_session_parses_matching_grades_case_insensitively():
    chat = FakeChat(
        grading_reply([{"concept": "gradient descent", "outcome": "correct_with_application", "quality": 0.95, "rationale": "cleared the transfer question"}])
    )

    evidence = grade_session("session-1", "classical-ml", ["Gradient descent"], "...", _chat_fn=chat)

    assert len(evidence) == 1
    assert evidence[0].concept == "Gradient descent"
    assert evidence[0].domain == "classical-ml"
    assert evidence[0].outcome == "correct_with_application"
    assert evidence[0].quality == 0.95
    assert evidence[0].source == "session_grading"
    assert evidence[0].session_id == "session-1"


def test_grade_session_defaults_omitted_concepts_to_not_reached():
    chat = FakeChat(grading_reply([{"concept": "Gradient descent", "outcome": "correct", "quality": 0.9, "rationale": "x"}]))

    evidence = grade_session("session-1", "classical-ml", ["Gradient descent", "Optimizer"], "...", _chat_fn=chat)

    by_concept = {e.concept: e for e in evidence}
    assert by_concept["Gradient descent"].outcome == "correct"
    assert by_concept["Optimizer"].outcome == "not_reached"
    assert by_concept["Optimizer"].quality == 0.0


def test_grade_session_writes_rationale_to_the_session_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chat = FakeChat(
        grading_reply(
            [
                {
                    "concept": "Gradient descent",
                    "outcome": "correct_with_application",
                    "quality": 0.95,
                    "rationale": "cleared the rocket-trajectory transfer question",
                }
            ]
        )
    )
    log = SessionLog("session-1")

    grade_session("session-1", "classical-ml", ["Gradient descent"], "...", log=log, _chat_fn=chat)
    log.close()

    contents = log.path.read_text(encoding="utf-8")
    assert "GRADE: Gradient descent -> correct_with_application" in contents
    assert "cleared the rocket-trajectory transfer question" in contents


def test_grade_session_logs_not_reached_for_omitted_concepts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chat = FakeChat(grading_reply([{"concept": "Gradient descent", "outcome": "correct", "quality": 0.9, "rationale": "x"}]))
    log = SessionLog("session-1")

    grade_session("session-1", "classical-ml", ["Gradient descent", "Optimizer"], "...", log=log, _chat_fn=chat)
    log.close()

    contents = log.path.read_text(encoding="utf-8")
    assert "GRADE: Optimizer -> not_reached" in contents
