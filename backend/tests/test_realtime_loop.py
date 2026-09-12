import asyncio
import json

from learning_os.conversation.prompt import END_SESSION_NUDGE
from learning_os.realtime.loop import _session_config, handle_tool_call, open_session, request_closing
from learning_os.sessions.models import SessionPlan


def make_plan(domain: str = "physics") -> SessionPlan:
    return SessionPlan(
        session_id="session-1",
        domain=domain,
        objective="Review Electromagnetism",
        concepts=["Electromagnetism"],
        target_difficulty="foundational",
        expected_duration_minutes=15,
    )


def test_session_config_enables_far_field_noise_reduction():
    config = _session_config(make_plan())

    assert config["audio"]["input"]["noise_reduction"] == {"type": "far_field"}


def test_session_config_sets_english_language_hint_for_non_language_domain():
    config = _session_config(make_plan(domain="physics"))

    assert config["audio"]["input"]["transcription"]["language"] == "en"


def test_session_config_omits_language_hint_for_language_domain():
    """A learner practicing Turkish may genuinely be speaking Turkish, not
    English -- forcing "en" here would actively hurt transcription."""
    config = _session_config(make_plan(domain="turkish"))

    assert "language" not in config["audio"]["input"]["transcription"]


def test_session_config_raises_silence_duration_above_the_sdk_default():
    """decisions.md #59: a real session split one answer into unrelated
    fragments because a mid-thought pause read as "done talking"."""
    config = _session_config(make_plan())

    assert config["audio"]["input"]["turn_detection"]["silence_duration_ms"] == 800


def test_session_config_passes_planned_concepts_as_transcription_keywords():
    """decisions.md #61: domain vocabulary ("Electromagnetism", "GraphRAG")
    is exactly what a generic transcription model tends to mis-hear."""
    plan = make_plan()

    config = _session_config(plan)

    assert config["audio"]["input"]["transcription"]["keywords"] == plan.concepts


def test_session_config_reads_transcription_model_from_settings(monkeypatch):
    from learning_os import config as config_module

    config_module.get_settings.cache_clear()
    monkeypatch.setenv("OPENAI_REALTIME_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")

    config = _session_config(make_plan())

    assert config["audio"]["input"]["transcription"]["model"] == "gpt-4o-mini-transcribe"
    config_module.get_settings.cache_clear()


def test_handle_tool_call_runs_synchronous_work_in_a_thread(monkeypatch):
    """decisions.md #59: a slow synchronous tool call (real vault I/O, a
    first-ever ~2s vault-index build) must not stall the rest of this
    loop's event processing -- confirmed here by proving a concurrently
    scheduled task keeps ticking while the "tool call" is blocking-sleeping
    on a real OS thread, not the event loop."""
    import time

    from learning_os.realtime import loop as loop_module

    def slow_sync_tool(name, **kwargs):  # matches the real call_tool(name, **kwargs) signature
        time.sleep(0.2)
        return {"ok": True}

    monkeypatch.setattr(loop_module, "call_tool", slow_sync_tool)

    async def scenario() -> int:
        ticks = 0
        stop = False

        async def tick_counter() -> None:
            nonlocal ticks
            while not stop:
                ticks += 1
                await asyncio.sleep(0.01)

        counter_task = asyncio.create_task(tick_counter())
        await loop_module.handle_tool_call("whatever", {})
        stop = True
        await counter_task
        return ticks

    ticks = asyncio.run(scenario())

    assert ticks > 5  # the event loop kept running many ticks during the 0.2s "tool call"


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
