"""One-time (but idempotent, safe to re-run) regrading of real historical
session logs into decisions.md #44's evidence table. Not part of the live
tutoring path -- finish_session grades a session as it ends; this exists
purely to seed real evidence from sessions that predate the two-sided
store, per #44's build-order step 4."""

import argparse
import ast
import re
import sys

from learning_os.llm_client import chat_completion
from learning_os.mistakes import record_evidence
from learning_os.mistakes.store import query_evidence
from learning_os.session_log import LOG_DIR, SessionLog
from learning_os.sessions.grading import grade_session

_SESSION_START_PATTERN = re.compile(
    r"SESSION START domain=(?P<domain>.*?) objective=(?P<objective>.*?) concepts=(?P<concepts>\[.*\])\s*$"
)


def _parse_session_start(first_line: str) -> tuple[str, list[str]] | None:
    match = _SESSION_START_PATTERN.search(first_line)
    if not match:
        return None
    domain = ast.literal_eval(match.group("domain"))
    concepts = ast.literal_eval(match.group("concepts"))
    return domain, concepts


def backfill_session(log_path) -> str:
    """Returns a one-line human-readable result for this log. Idempotent:
    a session that already has evidence rows (from a real finish_session
    call, or a previous backfill run) is skipped, never re-graded."""
    session_id = log_path.stem

    if query_evidence(session_id=session_id):
        return f"{session_id}: already graded, skipped"

    transcript = log_path.read_text(encoding="utf-8")
    first_line = transcript.splitlines()[0] if transcript else ""
    parsed = _parse_session_start(first_line)
    if parsed is None:
        return f"{session_id}: no SESSION START line found, skipped"
    domain, concepts = parsed

    log = SessionLog(session_id)
    try:
        evidence = grade_session(session_id, domain, concepts, transcript, log=log, _chat_fn=chat_completion)
    except Exception as exc:  # noqa: BLE001 -- one bad log must not stop the rest of the backfill
        log.write(f"BACKFILL GRADING FAILED: {exc}")
        return f"{session_id}: grading failed ({exc})"
    finally:
        log.close()

    record_evidence(evidence)
    outcomes = ", ".join(f"{e.concept}={e.outcome}" for e in evidence)
    return f"{session_id}: graded {len(evidence)} concepts -- {outcomes}"


def run() -> None:
    parser = argparse.ArgumentParser(
        description="Regrade real historical session logs into the evidence table (decisions.md #44)."
    )
    parser.parse_args()

    log_paths = sorted(LOG_DIR.glob("*.log"))
    if not log_paths:
        print(f"No session logs found under {LOG_DIR}.")
        return

    for log_path in log_paths:
        result = backfill_session(log_path)
        print(result, file=sys.stdout)


if __name__ == "__main__":
    run()
