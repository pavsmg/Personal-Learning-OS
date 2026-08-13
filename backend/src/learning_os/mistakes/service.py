from datetime import UTC, datetime

from learning_os.mistakes import store
from learning_os.mistakes.models import MasteryEstimate, MistakeEntry

DEFAULT_CONCEPTUAL_UNDERSTANDING = 1.0
MIN_REVIEW_INTERVAL_DAYS = 1.0
MAX_REVIEW_INTERVAL_DAYS = 14.0


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


def _review_interval_days(understanding: float) -> float:
    """Naive v1 spaced-repetition interval: linear between 1 day (no real
    understanding yet) and 14 days (well understood) — no need for
    anything smarter than that to be a real improvement over having no
    time component in scheduling at all."""
    return MIN_REVIEW_INTERVAL_DAYS + understanding * (MAX_REVIEW_INTERVAL_DAYS - MIN_REVIEW_INTERVAL_DAYS)


def _overdue_ratio(mistakes: list[MistakeEntry], now: datetime) -> float:
    """>1 means overdue relative to this concept's own interval, <1 means
    not due yet. A single ratio (rather than a due/not-due split) lets a
    long-overdue well-understood concept still outrank a barely-overdue
    poorly-understood one when that's actually true, and keeps not-yet-due
    concepts meaningfully ordered too (soonest-due-next first) instead of
    just tied at the bottom. days_since is rounded to the nearest whole
    day, not left as a raw fractional value: several mistakes saved
    seconds apart in the same real session (the common case) would
    otherwise get near-zero but essentially random relative ratios from
    floating-point/wall-clock noise, not a meaningful signal — rounding
    makes same-day entries genuinely tie so they fall through to the
    understanding-based tiebreak in recommend_review instead."""
    understanding = _conceptual_understanding(mistakes)
    most_recent = max(m.timestamp for m in mistakes)
    days_since = round((now - most_recent).total_seconds() / 86400)
    return days_since / _review_interval_days(understanding)


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


def recommend_review_scored(domain: str | None = None) -> list[tuple[str, float]]:
    """Same ranking as recommend_review, with each concept's raw
    _overdue_ratio attached. Exists so sessions/service.py's automatic-mode
    planner can layer vault centrality on top of pure urgency without
    recomputing it, while recommend_review itself -- a registered
    model-facing tool (tools.md) -- keeps its list[str] contract and
    ordering byte-for-byte unchanged."""
    mistakes = store.query_mistakes(domain=domain)
    by_concept: dict[str, list[MistakeEntry]] = {}
    for mistake in mistakes:
        by_concept.setdefault(mistake.concept, []).append(mistake)

    now = datetime.now(UTC)
    scored = [
        (concept, _overdue_ratio(concept_mistakes, now), _conceptual_understanding(concept_mistakes))
        for concept, concept_mistakes in by_concept.items()
    ]
    scored.sort(key=lambda item: (-item[1], item[2]))
    return [(concept, ratio) for concept, ratio, _ in scored]


def recommend_review(domain: str | None = None) -> list[str]:
    """Ranked by spaced-repetition urgency (`_overdue_ratio`), not just raw
    understanding: a concept reviewed long ago outranks one reviewed
    yesterday even if the latter's understanding score is worse, once the
    former is more overdue relative to its own interval. Concepts tied on
    urgency (most commonly: several reviewed today) fall back to raw
    understanding, worst first — the previous, only ranking signal. Still
    returns every tracked concept, just reordered — no filtering to "due
    only," so automatic-mode session planning never starts erroring just
    because nothing is strictly overdue yet.

    Thin wrapper over recommend_review_scored, which does the ranking and
    also exposes each concept's raw overdue_ratio for internal callers.
    This function's own contract -- list[str], same ordering -- is
    unchanged."""
    return [concept for concept, _ in recommend_review_scored(domain)]


def recommend_domain() -> str | None:
    """Which domain has gone longest without any tracked activity — the
    domain-level analog of recommend_review's per-concept spacing.
    Without this, automatic-mode session planning picked the single
    globally worst-ranked concept regardless of domain: one domain with a
    stubbornly bad or frequently-recurring concept could dominate every
    automatic session indefinitely while other domains never got a turn.
    Returns None if there's no mistake data for any domain yet."""
    mistakes = store.query_mistakes()
    if not mistakes:
        return None

    last_seen: dict[str, datetime] = {}
    for mistake in mistakes:
        current = last_seen.get(mistake.domain)
        if current is None or mistake.timestamp > current:
            last_seen[mistake.domain] = mistake.timestamp

    return min(last_seen, key=lambda domain: last_seen[domain])
