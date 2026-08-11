from datetime import UTC, datetime

from learning_os.mistakes import store
from learning_os.mistakes.models import MasteryEstimate, MistakeEntry

DEFAULT_CONCEPTUAL_UNDERSTANDING = 1.0


def save_mistake(
    concept: str,
    explanation: str,
    category: str,
    severity: str,
    confidence: float,
    domain: str,
    related_notes: list[str] | None = None,
) -> MistakeEntry:
    """corrected=False at save time: this records that the tutor flagged and
    explained the mistake, not that the learner has since demonstrated they
    understand it. Nothing in this milestone re-verifies and flips it."""
    entry = MistakeEntry(
        domain=domain,
        concept=concept,
        explanation=explanation,
        category=category,
        severity=severity,
        timestamp=datetime.now(UTC),
        corrected=False,
        confidence=confidence,
        related_notes=related_notes or [],
    )
    store.insert_mistake(entry)
    return entry


def search_mistakes(query: str, limit: int = 10) -> list[MistakeEntry]:
    return store.query_mistakes(text=query, limit=limit)


def get_recent_mistakes(domain: str | None = None, limit: int = 10) -> list[MistakeEntry]:
    return store.query_mistakes(domain=domain, limit=limit, order_by_recent=True)


def _conceptual_understanding(mistakes: list[MistakeEntry]) -> float:
    if not mistakes:
        return DEFAULT_CONCEPTUAL_UNDERSTANDING
    average_confidence = sum(m.confidence for m in mistakes) / len(mistakes)
    return max(0.0, min(1.0, 1.0 - average_confidence))


def get_learning_profile(domain: str | None = None) -> list[MasteryEstimate]:
    mistakes = store.query_mistakes(domain=domain)
    by_domain_concept: dict[tuple[str, str], list[MistakeEntry]] = {}
    for mistake in mistakes:
        by_domain_concept.setdefault((mistake.domain, mistake.concept), []).append(mistake)

    return [
        MasteryEstimate(
            domain=mistake_domain,
            concept=concept,
            conceptual_understanding=_conceptual_understanding(concept_mistakes),
            mistake_count=len(concept_mistakes),
        )
        for (mistake_domain, concept), concept_mistakes in by_domain_concept.items()
    ]


def estimate_mastery(domain: str, concept: str) -> float:
    mistakes = store.query_mistakes(domain=domain, concept=concept)
    return _conceptual_understanding(mistakes)


def recommend_review(domain: str | None = None) -> list[str]:
    mistakes = store.query_mistakes(domain=domain)
    by_concept: dict[str, list[MistakeEntry]] = {}
    for mistake in mistakes:
        by_concept.setdefault(mistake.concept, []).append(mistake)

    ranked = sorted(by_concept.items(), key=lambda item: _conceptual_understanding(item[1]))
    return [concept for concept, _ in ranked]
