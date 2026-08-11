import asyncio
import base64
from collections.abc import AsyncIterator

SAMPLE_RATE = 24000
CHUNK_SIZE = 4096
ECHO_CANCEL_SOURCE = "learning_os_ec_source"
ECHO_CANCEL_SINK = "learning_os_ec_sink"


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
    proc = await asyncio.create_subprocess_exec("pactl", "unload-module", module_id)
    await proc.wait()


class Microphone:
    async def __aenter__(self) -> "Microphone":
        self._proc = await asyncio.create_subprocess_exec(
            "parec",
            f"--device={ECHO_CANCEL_SOURCE}",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            "--format=s16le",
            stdout=asyncio.subprocess.PIPE,
        )
        return self

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


class Speaker:
    def __init__(self) -> None:
        self._proc: asyncio.subprocess.Process | None = None

    async def start(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            "paplay",
            f"--device={ECHO_CANCEL_SINK}",
            "--raw",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            "--format=s16le",
            stdin=asyncio.subprocess.PIPE,
        )

    async def write(self, base64_audio: str) -> None:
        if self._proc is None or self._proc.stdin is None:
            return
        self._proc.stdin.write(base64.b64decode(base64_audio))
        await self._proc.stdin.drain()

    async def restart(self) -> None:
        """Cuts off whatever's still queued in the speaker immediately —
        the actual barge-in mechanism. Killing and respawning is simpler
        and more reliable than trying to flush a subprocess's audio
        buffer."""
        await self.stop()
        await self.start()

    async def stop(self) -> None:
        if self._proc is None:
            return
        self._proc.kill()
        await self._proc.wait()
        self._proc = None
