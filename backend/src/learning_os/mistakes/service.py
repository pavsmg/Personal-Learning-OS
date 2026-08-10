from learning_os.mistakes.models import MistakeEntry


def save_mistake(
    concept: str,
    explanation: str,
    category: str,
    severity: str,
    confidence: float,
    related_notes: list[str] | None = None,
) -> MistakeEntry:
    """Stub — implemented in Milestone 6."""
    raise NotImplementedError("save_mistake is not implemented yet (Milestone 6)")


def search_mistakes(query: str, limit: int = 10) -> list[MistakeEntry]:
    """Stub — implemented in Milestone 6."""
    raise NotImplementedError("search_mistakes is not implemented yet (Milestone 6)")


def get_recent_mistakes(domain: str | None = None, limit: int = 10) -> list[MistakeEntry]:
    """Stub — implemented in Milestone 6."""
    raise NotImplementedError("get_recent_mistakes is not implemented yet (Milestone 6)")
