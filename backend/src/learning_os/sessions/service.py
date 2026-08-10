import uuid

from learning_os.retrieval import related_notes, search_notes
from learning_os.sessions.models import SessionPlan, SessionSummary

DEFAULT_TARGET_DIFFICULTY = "beginner"
MINUTES_PER_CONCEPT = 5
MINIMUM_DURATION_MINUTES = 15


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

    return SessionPlan(
        session_id=str(uuid.uuid4()),
        objective=f"Review {anchor_title} and related concepts",
        concepts=concepts,
        target_difficulty=DEFAULT_TARGET_DIFFICULTY,
        expected_duration_minutes=duration,
    )


def finish_session(session_id: str) -> None:
    """Stub — session lifecycle continues in Milestone 5."""
    raise NotImplementedError("finish_session is not implemented yet (Milestone 5)")


def summarize_session(session_id: str) -> SessionSummary:
    """Stub — session lifecycle continues in Milestone 5."""
    raise NotImplementedError("summarize_session is not implemented yet (Milestone 5)")
