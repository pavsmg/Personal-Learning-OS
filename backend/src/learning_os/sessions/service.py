import uuid
from dataclasses import dataclass, field

from learning_os.retrieval import related_notes, search_notes
from learning_os.sessions.models import SessionPlan, SessionSummary

DEFAULT_TARGET_DIFFICULTY = "beginner"
MINUTES_PER_CONCEPT = 5
MINIMUM_DURATION_MINUTES = 15


@dataclass
class _SessionRecord:
    plan: SessionPlan
    turns: list[tuple[str, str]] = field(default_factory=list)
    finished: bool = False


_SESSIONS: dict[str, _SessionRecord] = {}


def create_session(topic: str, max_concepts: int = 5) -> SessionPlan:
    """Naive v1 heuristic: anchor on the best search match, expand via
    related_notes. target_difficulty/expected_duration_minutes are fixed
    defaults for now — mistake/mastery data to inform them doesn't exist
    until Milestone 6."""
    matches = search_notes(topic, limit=1)
    if not matches:
        raise ValueError(f"No vault notes found for topic: {topic!r}")

    anchor_title = matches[0].title
    concepts = [anchor_title]
    for note in related_notes(anchor_title):
        if len(concepts) >= max_concepts:
            break
        concepts.append(note.title)

    duration = max(MINIMUM_DURATION_MINUTES, MINUTES_PER_CONCEPT * len(concepts))

    plan = SessionPlan(
        session_id=str(uuid.uuid4()),
        objective=f"Review {anchor_title} and related concepts",
        concepts=concepts,
        target_difficulty=DEFAULT_TARGET_DIFFICULTY,
        expected_duration_minutes=duration,
    )
    _SESSIONS[plan.session_id] = _SessionRecord(plan=plan)
    return plan


def record_turn(session_id: str, role: str, content: str) -> None:
    _SESSIONS[session_id].turns.append((role, content))


def finish_session(session_id: str) -> None:
    if session_id not in _SESSIONS:
        raise KeyError(f"Unknown session: {session_id}")
    _SESSIONS[session_id].finished = True


def summarize_session(session_id: str) -> SessionSummary:
    if session_id not in _SESSIONS:
        raise KeyError(f"Unknown session: {session_id}")

    record = _SESSIONS[session_id]
    transcript = " ".join(content.lower() for _, content in record.turns)
    concepts_reinforced = [c for c in record.plan.concepts if c.lower() in transcript]

    summary = (
        f"Session on {record.plan.objective!r}: {len(record.turns)} exchanges. "
        + (
            f"Concepts reinforced: {', '.join(concepts_reinforced)}."
            if concepts_reinforced
            else "No plan concepts were confirmed as discussed."
        )
    )

    return SessionSummary(
        session_id=session_id,
        summary=summary,
        concepts_reinforced=concepts_reinforced,
    )
