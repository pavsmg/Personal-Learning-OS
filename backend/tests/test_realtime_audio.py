import asyncio
import base64
import time

import pytest

from learning_os.realtime.audio import BYTES_PER_SAMPLE, SAMPLE_RATE, Speaker, _advance_deadline, _chunk_duration_seconds

ONE_SECOND_OF_AUDIO_BYTES = SAMPLE_RATE * BYTES_PER_SAMPLE


def test_chunk_duration_seconds():
    assert _chunk_duration_seconds(ONE_SECOND_OF_AUDIO_BYTES) == pytest.approx(1.0)
    assert _chunk_duration_seconds(0) == 0.0


def test_advance_deadline_from_none_starts_at_now_plus_duration():
    assert _advance_deadline(None, now=10.0, duration=0.5) == pytest.approx(10.5)


def test_advance_deadline_stacks_when_still_behind():
    """A second write arriving before the first has finished "playing"
    (deadline still in the future) extends the deadline further out."""
    assert _advance_deadline(10.5, now=10.2, duration=0.5) == pytest.approx(11.0)


def test_advance_deadline_resets_from_now_after_an_idle_gap():
    """decisions.md #61: the bug #59's fix actually had. An old deadline
    that's already in the past (the learner talked for a while, or there
    was a thinking pause) must not make future writes look like they have
    a huge backlog -- the deadline should restart from "now"."""
    assert _advance_deadline(10.5, now=185.0, duration=0.5) == pytest.approx(185.5)


def test_advance_deadline_exactly_at_now_still_advances():
    assert _advance_deadline(10.0, now=10.0, duration=0.25) == pytest.approx(10.25)


class FakeStdin:
    def __init__(self) -> None:
        self.written = bytearray()

    def write(self, data: bytes) -> None:
        self.written.extend(data)

    async def drain(self) -> None:
        pass


class FakeStderr:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class FakeProcess:
    def __init__(self) -> None:
        self.stdin = FakeStdin()
        self.stderr = FakeStderr()
        self.killed = False

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> None:
        return None


async def _fake_create_subprocess_exec(*args, **kwargs):
    return FakeProcess()


def test_speaker_wait_until_drained_waits_for_queued_audio(monkeypatch):
    """Integration-level check that Speaker.write/_writer_loop/
    wait_until_drained connect correctly, not just the arithmetic in
    isolation (decisions.md #61) -- no real audio hardware needed, the
    subprocess is faked."""
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)

    async def scenario() -> float:
        speaker = Speaker()
        await speaker.start()
        raw = b"\x00" * int(0.15 * SAMPLE_RATE * BYTES_PER_SAMPLE)
        written = await speaker.write(base64.b64encode(raw).decode())
        assert written == len(raw)

        start = time.monotonic()
        await speaker.wait_until_drained()
        elapsed = time.monotonic() - start
        await speaker.stop()
        return elapsed

    elapsed = asyncio.run(scenario())
    assert elapsed >= 0.1  # waited roughly the queued audio's real duration, not zero


def test_speaker_wait_until_drained_is_instant_with_nothing_queued(monkeypatch):
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)

    async def scenario() -> None:
        speaker = Speaker()
        await speaker.start()
        await speaker.wait_until_drained()  # should not hang or sleep
        await speaker.stop()

    asyncio.run(scenario())
