import asyncio
import base64
import sys
from collections.abc import AsyncIterator

SAMPLE_RATE = 24000
CHUNK_SIZE = 4096
ECHO_CANCEL_SOURCE = "learning_os_ec_source"
ECHO_CANCEL_SINK = "learning_os_ec_sink"
BYTES_PER_SAMPLE = 2  # s16le, mono


async def load_echo_cancel_module() -> str:
    """Loads PipeWire's echo-cancel module: a virtual sink to play the
    assistant's voice into, and a virtual source exposing the mic with that
    same audio subtracted back out (WebRTC AEC) — lets the mic stay live
    while the assistant is talking without hearing itself. Same approach as
    Language-Lab/realtime-test/index.js, ported from Node's execSync."""
    proc = await asyncio.create_subprocess_exec(
        "pactl",
        "load-module",
        "module-echo-cancel",
        f"source_name={ECHO_CANCEL_SOURCE}",
        f"sink_name={ECHO_CANCEL_SINK}",
        f"rate={SAMPLE_RATE}",
        "channels=1",
        "aec_method=webrtc",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Could not load module-echo-cancel — is PipeWire running? {stderr.decode().strip()}")
    return stdout.decode().strip()


async def unload_module(module_id: str) -> None:
    """Reports a failed unload rather than assuming success -- a silent
    failure here is exactly what leaves a stale learning_os_ec_source/sink
    behind for the next session to collide with (decisions.md #61)."""
    proc = await asyncio.create_subprocess_exec(
        "pactl", "unload-module", module_id, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        print(f"[audio] failed to unload module {module_id}: {stderr.decode().strip()}", file=sys.stderr)


async def reap_stale_echo_cancel_modules() -> None:
    """Idempotent startup safety net: if a previous run was killed hard
    (SIGKILL, OOM, terminal closed) before it could unload its module, the
    fixed source/sink names would otherwise collide with this run's fresh
    load. Finds and unloads any module-echo-cancel instance already using
    our names before loading a new one (decisions.md #61)."""
    proc = await asyncio.create_subprocess_exec(
        "pactl", "list", "short", "modules", stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    for line in stdout.decode().splitlines():
        fields = line.split("\t")
        if len(fields) < 3 or fields[1] != "module-echo-cancel":
            continue
        if ECHO_CANCEL_SOURCE in fields[2] or ECHO_CANCEL_SINK in fields[2]:
            await unload_module(fields[0])


class Microphone:
    async def __aenter__(self) -> "Microphone":
        self._proc = await asyncio.create_subprocess_exec(
            "parec",
            f"--device={ECHO_CANCEL_SOURCE}",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            "--format=s16le",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._stderr_task = asyncio.create_task(self._log_stderr())
        return self

    async def _log_stderr(self) -> None:
        assert self._proc.stderr is not None
        async for line in self._proc.stderr:
            print(f"[parec] {line.decode(errors='replace').rstrip()}", file=sys.stderr)

    async def chunks(self) -> AsyncIterator[str]:
        assert self._proc.stdout is not None
        while True:
            chunk = await self._proc.stdout.read(CHUNK_SIZE)
            if not chunk:
                return
            yield base64.b64encode(chunk).decode()

    async def __aexit__(self, *exc_info: object) -> None:
        self._proc.kill()
        await self._proc.wait()
        self._stderr_task.cancel()
        await asyncio.gather(self._stderr_task, return_exceptions=True)


def _chunk_duration_seconds(byte_count: int) -> float:
    return byte_count / (SAMPLE_RATE * BYTES_PER_SAMPLE)


def _advance_deadline(deadline: float | None, now: float, duration: float) -> float:
    """The virtual timestamp at which everything queued so far will have
    finished playing. Advances from whichever is later, the previous
    deadline or now -- so an idle gap (the learner talking, a thinking
    pause) before a write doesn't count as backlog, only audio that's
    genuinely still queued does. Split out as pure arithmetic so it's
    testable without real subprocess/wall-clock timing (decisions.md #61
    fixed a real bug here: the original implementation measured elapsed
    time since the *first* write of the whole speaker lifetime, so any
    idle gap made wait_until_drained's estimate go permanently negative --
    a no-op instead of an actual wait, on every closing recap that
    followed a normal multi-minute conversation)."""
    return max(deadline if deadline is not None else now, now) + duration


class Speaker:
    def __init__(self) -> None:
        self._proc: asyncio.subprocess.Process | None = None
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._writer_task: asyncio.Task[None] | None = None
        self._deadline: float | None = None

    async def start(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            "paplay",
            f"--device={ECHO_CANCEL_SINK}",
            "--raw",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            "--format=s16le",
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._queue = asyncio.Queue()
        self._deadline = None
        self._writer_task = asyncio.create_task(self._writer_loop())

    async def _writer_loop(self) -> None:
        """Owns the actual write()+drain() to paplay's stdin, decoupled
        from whoever calls Speaker.write() -- previously that await ran
        inline in the main event-dispatch loop, so paplay backpressure
        (drain() blocking until it catches up consuming) stalled dispatch
        of every other event, including barge-in detection, for however
        long the backlog took to clear (decisions.md #61)."""
        assert self._proc is not None and self._proc.stdin is not None
        stdin = self._proc.stdin
        stderr_task = asyncio.create_task(self._log_stderr())
        try:
            while True:
                raw = await self._queue.get()
                try:
                    stdin.write(raw)
                    await stdin.drain()
                except (BrokenPipeError, ConnectionResetError) as exc:
                    # paplay died mid-session (sink removed, PipeWire
                    # restart) -- drop remaining audio rather than crash
                    # the whole voice session on a write to a dead pipe.
                    print(f"[audio] speaker pipe closed unexpectedly: {exc}", file=sys.stderr)
                    self._queue.task_done()
                    break
                self._queue.task_done()
        finally:
            stderr_task.cancel()
            await asyncio.gather(stderr_task, return_exceptions=True)

    async def _log_stderr(self) -> None:
        assert self._proc is not None and self._proc.stderr is not None
        async for line in self._proc.stderr:
            print(f"[paplay] {line.decode(errors='replace').rstrip()}", file=sys.stderr)

    async def write(self, base64_audio: str) -> int:
        """Queues audio for playback and returns immediately -- the actual
        write happens in _writer_loop. Returns the raw byte count written,
        so a caller tracking per-item playback position (for
        conversation.item.truncate on barge-in) doesn't have to decode the
        base64 payload a second time."""
        if self._proc is None:
            return 0
        raw = base64.b64decode(base64_audio)
        now = asyncio.get_running_loop().time()
        self._deadline = _advance_deadline(self._deadline, now, _chunk_duration_seconds(len(raw)))
        await self._queue.put(raw)
        return len(raw)

    async def wait_until_drained(self) -> None:
        """response.done only means the server finished generating and
        sending audio -- it says nothing about whether paplay has actually
        finished *playing* what's already been queued. Killing the speaker
        right after response.done, unconditionally, cuts off whatever's
        still queued -- heard as the voice getting cut off mid-sentence,
        confirmed on a real closing turn (decisions.md #59). Waits for the
        writer to finish draining the queue, then for the virtual deadline
        (decisions.md #61's fix for #59's broken estimate) to actually
        pass."""
        if self._deadline is None:
            return
        await self._queue.join()
        remaining = self._deadline - asyncio.get_running_loop().time()
        if remaining > 0:
            await asyncio.sleep(remaining)

    async def restart(self) -> None:
        """Cuts off whatever's still queued in the speaker immediately —
        the actual barge-in mechanism. Killing and respawning is simpler
        and more reliable than trying to flush a subprocess's audio
        buffer. Deliberately does NOT wait_until_drained first: barge-in
        means the learner wants to interrupt right now, not once the
        assistant finishes its sentence."""
        await self.stop()
        await self.start()

    async def stop(self) -> None:
        if self._writer_task is not None:
            self._writer_task.cancel()
            await asyncio.gather(self._writer_task, return_exceptions=True)
            self._writer_task = None
        if self._proc is not None:
            self._proc.kill()
            await self._proc.wait()
            self._proc = None
