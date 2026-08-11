from datetime import UTC, datetime
from pathlib import Path

LOG_DIR = Path("logs")


class SessionLog:
    """Plain-text per-session transcript + tool-call log, written to
    logs/<session_id>.log as the session happens. Not the same thing as
    Milestone 9's session-lifecycle persistence (record_turn/
    summarize_session) — this is just a local, human-readable record for
    reviewing what happened in a voice session, since nothing else does
    that yet."""

    def __init__(self, session_id: str) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = LOG_DIR / f"{session_id}.log"
        self._file = self.path.open("a", encoding="utf-8")

    def write(self, line: str) -> None:
        timestamp = datetime.now(UTC).strftime("%H:%M:%S")
        self._file.write(f"[{timestamp}] {line}\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
