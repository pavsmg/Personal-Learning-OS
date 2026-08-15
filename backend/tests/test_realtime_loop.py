import asyncio
import json

from learning_os.conversation.prompt import END_SESSION_NUDGE
from learning_os.realtime.loop import handle_tool_call, open_session, request_closing


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")


def test_handle_tool_call_dispatches_to_real_search_notes(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept.\n"})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    output = asyncio.run(handle_tool_call("search_notes", {"query": "gradient descent"}))

    results = json.loads(output)
    assert results[0]["title"] == "Gradient descent"


def test_handle_tool_call_unknown_tool_returns_error_json_not_raise():
    output = asyncio.run(handle_tool_call("does_not_exist", {}))

    result = json.loads(output)
    assert "does_not_exist" in result["error"]


def test_handle_tool_call_handler_exception_returns_error_json_not_raise(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    output = asyncio.run(handle_tool_call("get_note", {}))  # missing required 'title' arg

    result = json.loads(output)
    assert "error" in result


class FakeConnection:
    """Records what gets sent over the Realtime protocol, in order. The audio
    and event plumbing around it stays untested (it needs real devices); what
    these tests pin down is that the right messages are sent at all, which is
    exactly what was missing before decisions.md #48."""

    def __init__(self):
        self.sent: list[tuple[str, object]] = []
        outer = self

        class _Item:
            async def create(self, item):
                outer.sent.append(("item", item))

        class _Conversation:
            item = _Item()

        class _Response:
            async def create(self):
                outer.sent.append(("response.create", None))

        self.conversation = _Conversation()
        self.response = _Response()


def test_open_session_asks_the_model_to_speak_first():
    """Rule 8: the tutor opens. Over Realtime that only happens if a response
    is explicitly created — otherwise it waits for the learner."""
    connection = FakeConnection()

    asyncio.run(open_session(connection))

    assert connection.sent == [("response.create", None)]


def test_request_closing_sends_the_nudge_then_asks_for_the_wrap_up():
    connection = FakeConnection()

    asyncio.run(request_closing(connection))

    kinds = [kind for kind, _ in connection.sent]
    assert kinds == ["item", "response.create"]
    item = connection.sent[0][1]
    assert item["role"] == "user"
    assert item["content"][0]["text"] == END_SESSION_NUDGE


def test_both_modes_end_a_session_with_the_same_nudge():
    """A wrap-up that differed by modality would make them two tutors."""
    from learning_os.conversation.loop import END_SESSION_NUDGE as text_nudge

    assert text_nudge is END_SESSION_NUDGE
