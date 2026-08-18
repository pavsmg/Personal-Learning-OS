from datetime import UTC, datetime
from typing import Any, Callable

from learning_os.llm_client import LLMReply, chat_completion
from learning_os.mistakes.models import Evidence
from learning_os.session_log import SessionLog
from learning_os.sessions.grading_prompt import build_grading_prompt
from learning_os.sessions.models import GradingResult

ChatFn = Callable[..., LLMReply]

_RECORD_SESSION_GRADES_TOOL = {
    "type": "function",
    "function": {
        "name": "record_session_grades",
        "description": "Record the graded outcome for every planned concept in this session.",
        "parameters": GradingResult.model_json_schema(),
    },
}
_RECORD_SESSION_GRADES_TOOL_CHOICE = {"type": "function", "function": {"name": "record_session_grades"}}


def grade_session(
    session_id: str,
    domain: str,
    concepts: list[str],
    transcript: str,
    log: SessionLog | None = None,
    _chat_fn: ChatFn = chat_completion,
) -> list[Evidence]:
    """decisions.md #44 point 2: one judged LLM pass over the transcript at
    session end, not a per-turn tool call. No inner try/except around the
    parse -- mirrors career/service.py's analyze_job_fit precedent; a
    malformed response raises here and is caught by finish_session's outer
    swallow-to-stderr.

    Every planned concept gets exactly one Evidence row, even if the
    model's response omits one (defaults to not_reached rather than being
    silently dropped) -- belt-and-suspenders beyond the prompt's own
    instruction to grade every concept.

    Each grade's rationale (required on ConceptGrade, but not a column on
    Evidence itself) is written to `log` when given, so a
    correct_with_application grade's justification is sampleable
    afterward against pedagogy.md's "cite the real transfer exchange, not
    a fluent-sounding transcript" requirement."""
    reply = _chat_fn(
        [{"role": "user", "content": build_grading_prompt(domain, concepts, transcript)}],
        [_RECORD_SESSION_GRADES_TOOL],
        tool_choice=_RECORD_SESSION_GRADES_TOOL_CHOICE,
    )
    arguments: dict[str, Any] = reply.tool_calls[0].arguments
    result = GradingResult(**arguments)
    graded = {grade.concept.lower(): grade for grade in result.grades}

    now = datetime.now(UTC)
    evidence = []
    for concept in concepts:
        grade = graded.get(concept.lower())
        if grade is None:
            evidence.append(
                Evidence(
                    domain=domain,
                    concept=concept,
                    timestamp=now,
                    outcome="not_reached",
                    quality=0.0,
                    source="session_grading",
                    session_id=session_id,
                )
            )
            if log is not None:
                log.write(f"GRADE: {concept} -> not_reached (model omitted this concept from its response)")
        else:
            evidence.append(
                Evidence(
                    domain=domain,
                    concept=concept,
                    timestamp=now,
                    outcome=grade.outcome,
                    quality=grade.quality,
                    source="session_grading",
                    session_id=session_id,
                )
            )
            if log is not None:
                log.write(f"GRADE: {concept} -> {grade.outcome} ({grade.rationale})")
    return evidence
