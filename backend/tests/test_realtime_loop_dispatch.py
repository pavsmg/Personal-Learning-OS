"""Integration-level tests for run_voice_session's live event-dispatch loop.

decisions.md #61 flagged this as a real gap: the existing FakeConnection in
test_realtime_loop.py only records outgoing calls, it can't simulate an
incoming event stream, so none of the response-id staleness filtering,
barge-in handling, or tool-call batching logic had any test coverage at
all -- only real voice sessions ever exercised it, which is how three
separate real bugs (#58, #59, #60) shipped in the first place. These tests
fake the audio subprocesses (Microphone/Speaker) and the Realtime
connection itself, but keep session creation, the real tool registry, and
grading real (with a faked, no-network finish_session) -- the same
boundary the rest of this test suite already draws elsewhere.
"""

import asyncio
import base64
import types

from learning_os.realtime import loop as loop_module


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")


class FakeMicrophone:
    """Never actually yields -- mirrors a real session where the mic
    streams for the whole session, only ending when cancelled at
    teardown."""

    async def __aenter__(self):
        return self

    async def chunks(self):
        await asyncio.Event().wait()
        yield  # pragma: no cover -- unreachable, keeps this an async generator

    async def __aexit__(self, *exc_info):
        return False


class FakeSpeaker:
    def __init__(self):
        self.written: list[bytes] = []
        self.restart_count = 0

    async def start(self):
        pass

    async def write(self, base64_audio: str) -> int:
        raw = base64.b64decode(base64_audio)
        self.written.append(raw)
        return len(raw)

    async def wait_until_drained(self):
        pass

    async def restart(self):
        self.restart_count += 1

    async def stop(self):
        pass


class _Recorder:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []


class _ResponseNamespace:
    def __init__(self, recorder: _Recorder):
        self._recorder = recorder

    async def create(self):
        self._recorder.calls.append(("response.create", None))

    async def cancel(self, **kwargs):
        self._recorder.calls.append(("response.cancel", kwargs))


class _ItemNamespace:
    def __init__(self, recorder: _Recorder):
        self._recorder = recorder

    async def create(self, item):
        self._recorder.calls.append(("item.create", item))

    async def truncate(self, **kwargs):
        self._recorder.calls.append(("item.truncate", kwargs))


class _ConversationNamespace:
    def __init__(self, recorder: _Recorder):
        self.item = _ItemNamespace(recorder)


class _SessionNamespace:
    def __init__(self, recorder: _Recorder):
        self._recorder = recorder

    async def update(self, session):
        self._recorder.calls.append(("session.update", session))


class _InputAudioBufferNamespace:
    async def append(self, audio):
        pass


class FakeRealtimeConnection(_Recorder):
    """Async-iterates a pre-scripted list of incoming events, and records
    every outgoing call the dispatch loop makes."""

    def __init__(self, events: list):
        super().__init__()
        self._events = list(events)
        self.response = _ResponseNamespace(self)
        self.conversation = _ConversationNamespace(self)
        self.session = _SessionNamespace(self)
        self.input_audio_buffer = _InputAudioBufferNamespace()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._events:
            raise StopAsyncIteration
        return self._events.pop(0)


class FakeConnectContextManager:
    def __init__(self, connection: FakeRealtimeConnection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, *exc_info):
        return False


class FakeRealtimeNamespace:
    def __init__(self, connection: FakeRealtimeConnection):
        self._connection = connection

    def connect(self, model):
        return FakeConnectContextManager(self._connection)


class FakeAsyncClient:
    def __init__(self, connection: FakeRealtimeConnection):
        self.realtime = FakeRealtimeNamespace(connection)


def ev(type_: str, **kwargs) -> types.SimpleNamespace:
    return types.SimpleNamespace(type=type_, **kwargs)


def patch_audio_layer(monkeypatch, connection: FakeRealtimeConnection, speaker: FakeSpeaker):
    monkeypatch.setattr(loop_module, "_get_async_client", lambda: FakeAsyncClient(connection))
    monkeypatch.setattr(loop_module, "Microphone", FakeMicrophone)
    monkeypatch.setattr(loop_module, "Speaker", lambda: speaker)
    monkeypatch.setattr(loop_module, "load_echo_cancel_module", _async_noop_str)
    monkeypatch.setattr(loop_module, "unload_module", _async_noop)
    monkeypatch.setattr(loop_module, "reap_stale_echo_cancel_modules", _async_noop)
    monkeypatch.setattr(loop_module, "finish_session", lambda *args, **kwargs: None)
    monkeypatch.setattr(loop_module, "SPEAKER_WARMUP_SECONDS", 0.0)


async def _async_noop(*args, **kwargs) -> None:
    return None


async def _async_noop_str(*args, **kwargs) -> str:
    return "fake-module-id"


def setup_env(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept.\n"})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))


def test_multiple_tool_calls_in_one_response_create_exactly_one_followup(tmp_path, monkeypatch):
    """decisions.md #61: a single response can request more than one tool
    call (confirmed in real logs -- search_notes and get_note in the same
    turn). Creating a response.create() per call, individually, used to
    race the server; now exactly one follow-up response is created after
    all of a turn's tool outputs are submitted."""
    setup_env(tmp_path, monkeypatch)
    events = [
        ev("response.created", response=types.SimpleNamespace(id="r1")),
        ev(
            "response.function_call_arguments.done",
            response_id="r1",
            call_id="c1",
            name="search_notes",
            arguments='{"query": "gradient descent"}',
            item_id="i1",
        ),
        ev(
            "response.function_call_arguments.done",
            response_id="r1",
            call_id="c2",
            name="get_note",
            arguments='{"title": "Gradient descent"}',
            item_id="i2",
        ),
        ev("response.done", response=types.SimpleNamespace(id="r1")),
    ]
    connection = FakeRealtimeConnection(events)
    speaker = FakeSpeaker()
    patch_audio_layer(monkeypatch, connection, speaker)

    asyncio.run(loop_module.run_voice_session("gradient descent"))

    response_creates = [call for call in connection.calls if call[0] == "response.create"]
    item_creates = [call for call in connection.calls if call[0] == "item.create"]
    # 2, not 3: one from open_session() opening the session, and exactly
    # one follow-up for the whole turn's tool calls -- the old, buggy
    # behavior would have added a *third*, one per individual tool call.
    assert len(response_creates) == 2
    assert len(item_creates) == 2
    assert {item["call_id"] for _, item in item_creates} == {"c1", "c2"}


def test_stale_events_from_a_cancelled_response_are_ignored(tmp_path, monkeypatch):
    """decisions.md #60/#61: after a barge-in, stray delta/done events for
    the response that was just abandoned must not be treated as belonging
    to whatever comes next."""
    setup_env(tmp_path, monkeypatch)
    events = [
        ev("response.created", response=types.SimpleNamespace(id="r1")),
        ev("response.output_audio_transcript.delta", response_id="r1", delta="Hello"),
        ev("input_audio_buffer.speech_started"),  # barge-in: invalidates r1
        # Stray leftovers from r1, arriving after the barge-in:
        ev("response.output_audio_transcript.delta", response_id="r1", delta=" world"),
        ev("response.output_audio.delta", response_id="r1", item_id="i1", delta=base64.b64encode(b"\x00\x00").decode()),
        ev("response.done", response=types.SimpleNamespace(id="r1")),
    ]
    connection = FakeRealtimeConnection(events)
    speaker = FakeSpeaker()
    patch_audio_layer(monkeypatch, connection, speaker)

    asyncio.run(loop_module.run_voice_session("gradient descent"))

    # The stray audio delta after the barge-in must never reach the speaker.
    assert speaker.written == []
    assert speaker.restart_count == 1


def test_barge_in_never_calls_response_cancel(tmp_path, monkeypatch):
    """decisions.md #61: server-side VAD already auto-cancels the in-flight
    response by default -- the client no longer sends its own redundant
    cancel, which is what produced the response_cancel_not_active errors
    #59/#60 had to build defenses around."""
    setup_env(tmp_path, monkeypatch)
    events = [
        ev("response.created", response=types.SimpleNamespace(id="r1")),
        ev("input_audio_buffer.speech_started"),
        ev("response.done", response=types.SimpleNamespace(id="r1")),
    ]
    connection = FakeRealtimeConnection(events)
    speaker = FakeSpeaker()
    patch_audio_layer(monkeypatch, connection, speaker)

    asyncio.run(loop_module.run_voice_session("gradient descent"))

    assert all(call[0] != "response.cancel" for call in connection.calls)
    assert speaker.restart_count == 1


def test_barge_in_truncates_the_played_portion_of_the_current_item(tmp_path, monkeypatch):
    """decisions.md #61: without this, the server keeps the full generated
    utterance in its conversation history even though local playback was
    cut off, so the model believes it said things the learner never heard."""
    setup_env(tmp_path, monkeypatch)
    raw = b"\x00" * 4800  # 0.1s of 24kHz s16le mono
    events = [
        ev("response.created", response=types.SimpleNamespace(id="r1")),
        ev("response.output_audio.delta", response_id="r1", item_id="i1", delta=base64.b64encode(raw).decode()),
        ev("input_audio_buffer.speech_started"),
        ev("response.done", response=types.SimpleNamespace(id="r1")),
    ]
    connection = FakeRealtimeConnection(events)
    speaker = FakeSpeaker()
    patch_audio_layer(monkeypatch, connection, speaker)

    asyncio.run(loop_module.run_voice_session("gradient descent"))

    truncate_calls = [call for call in connection.calls if call[0] == "item.truncate"]
    assert len(truncate_calls) == 1
    assert truncate_calls[0][1]["item_id"] == "i1"


def test_unhandled_event_types_are_logged_not_dropped(tmp_path, monkeypatch):
    setup_env(tmp_path, monkeypatch)
    events = [ev("rate_limits.updated", rate_limits=[])]
    connection = FakeRealtimeConnection(events)
    speaker = FakeSpeaker()
    patch_audio_layer(monkeypatch, connection, speaker)

    asyncio.run(loop_module.run_voice_session("gradient descent"))

    from learning_os import session_log as session_log_module

    log_files = list(session_log_module.LOG_DIR.glob("*.log"))
    assert log_files
    contents = log_files[0].read_text(encoding="utf-8")
    assert "UNHANDLED EVENT: rate_limits.updated" in contents
