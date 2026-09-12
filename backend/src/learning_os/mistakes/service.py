from dataclasses import dataclass
from datetime import UTC, datetime

from learning_os.mistakes import store
from learning_os.mistakes.models import Evidence, EvidenceReview, MasteryEstimate, MistakeEntry

# Mirrors sessions/service.py's DEFAULT_DOMAIN -- not imported, since
# sessions already depends on mistakes and importing back would cycle.
UNTRACKED_DOMAIN = "general"

# decisions.md #63: mistake explanations stay short by construction -- a
# one-line misconception summary for personalizing future questions, not
# a transcript fragment. Longer text is truncated on write (old rows are
# grandfathered, never rewritten by migration).
MAX_EXPLANATION_CHARS = 280

# --- decisions.md #44: fixed, documented scheduling constants ---
#
# FSRS_FACTOR/FSRS_DECAY are FSRS's own published forgetting-curve shape
# (R(t, S) = (1 + FACTOR*t/S)^DECAY), verified against current FSRS
# documentation before use, not from memory, per #44's explicit
# requirement. At FSRS_REQUEST_RETENTION=0.9 this curve has the property
# R(t=S) == 0.9 exactly, which is what makes _review_interval_days below a
# clean solve for t. Everything past these two constants is this project's
# own fixed v1 choice, never per-user fitted (#44's throughput argument:
# ~5 graded observations per 20-minute session vs. FSRS's own ~10^3-review
# fitting requirement) -- same "direction principled, magnitude isn't
# tuned" spirit as SHAKY_SETTLED_THRESHOLD/OVERDUE_TIE_BUCKET_SIZE
# elsewhere in this project. Revisit once real graded session volume
# exists to check against, not before.
FSRS_REQUEST_RETENTION = 0.9
FSRS_DECAY = -0.5
FSRS_FACTOR = 19 / 81

INITIAL_STABILITY_DAYS = 1.0  # one observation isn't enough to schedule far out
INITIAL_DIFFICULTY = 0.5  # midpoint -- no assumption before any evidence exists

# Stability multipliers for a successful observation, scaled by that
# observation's weight (confidence for a mistake-derived incorrect, quality
# for evidence) -- direction is application > correct > partial, matching
# pedagogy.md's ranking of a cleared rule-11 transfer question as the
# strongest signal this system can produce.
STABILITY_GROWTH_CORRECT_WITH_APPLICATION = 2.5
STABILITY_GROWTH_CORRECT = 1.8
STABILITY_GROWTH_PARTIAL = 1.15
STABILITY_DECAY_INCORRECT = 0.35  # mirrors FSRS's own sharp post-lapse stability cut

DIFFICULTY_DELTA_INCORRECT = 0.15
DIFFICULTY_DELTA_PARTIAL = 0.05
DIFFICULTY_DELTA_CORRECT = -0.05
DIFFICULTY_DELTA_CORRECT_WITH_APPLICATION = -0.10
DIFFICULTY_MIN = 0.1
DIFFICULTY_MAX = 0.95  # bounded so one streak can't pin a concept at an extreme permanently

MIN_REVIEW_INTERVAL_DAYS = 1.0
# Raised from 14 (decisions.md #44, user-confirmed): two-sided evidence can
# now honestly justify a longer gap for a demonstrably solid concept than a
# failures-only store ever could -- still well short of Anki's multi-month
# intervals, since this system won't have the observation density to trust
# further out for a long time.
MAX_REVIEW_INTERVAL_DAYS = 30.0


@dataclass(frozen=True)
class _Observation:
    """One scoring-eligible unit of evidence, from either table. weight is
    confidence for a mistake row, quality for an evidence row --
    "not_reached" evidence never becomes an _Observation at all (see
    _merge_observations): absence stays absence, decisions.md #44."""

    timestamp: datetime
    outcome: str  # "incorrect" | "partial" | "correct" | "correct_with_application"
    weight: float


def _merge_observations(mistakes: list[MistakeEntry], evidence: list[Evidence]) -> list[_Observation]:
    observations = [_Observation(timestamp=m.timestamp, outcome="incorrect", weight=m.confidence) for m in mistakes]
    observations += [
        _Observation(timestamp=e.timestamp, outcome=e.outcome, weight=e.quality)
        for e in evidence
        if e.outcome != "not_reached"
    ]
    return observations


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
    understand it. record_evidence flips it once a later `correct`/
    `correct_with_application` observation is graded for the same concept
    (decisions.md #44 point 6)."""
    entry = MistakeEntry(
        domain=domain,
        concept=concept,
        explanation=explanation[:MAX_EXPLANATION_CHARS],
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


def record_evidence(entries: list[Evidence]) -> dict[str, int]:
    """The single write path for two-sided evidence -- sessions/service.py's
    finish_session calls this once per session, with one entry per planned
    concept (decisions.md #44 point 2). A later correct/correct_with_
    application entry for a concept flips that concept's earlier mistakes
    rows to corrected=True (point 6); not_reached entries are still stored
    (so a planned-but-never-quizzed concept isn't silently dropped) but
    never trigger a correction flip.

    decisions.md #63: delegated to store.save_session_evidence -- one
    transaction per session, idempotent per (session_id, domain, concept)
    with first-write-wins. Returns {"inserted", "corrected"} counts."""
    return store.save_session_evidence(entries)


def record_evidence_review(
    session_id: str,
    concept: str,
    new_outcome: str,
    reason: str,
    domain: str | None = None,
    reviewer: str = "human",
) -> EvidenceReview:
    """Appends a human correction of one graded outcome (decisions.md #63,
    result-only). When the domain is omitted it must resolve to exactly
    one evidence row for (session_id, concept), else ValueError. A
    corrected-to-correct outcome flips matching mistakes to corrected,
    mirroring record_evidence; the original row is never edited."""
    candidates = store.query_evidence(session_id=session_id, concept=concept, domain=domain)
    if domain is None and len({c.domain.lower() for c in candidates}) > 1:
        raise ValueError(
            f"Concept {concept!r} in session {session_id!r} exists in "
            f"multiple domains -- pass --domain explicitly."
        )
    if not candidates:
        raise KeyError(f"No evidence for session={session_id!r} concept={concept!r}")
    target = candidates[0]
    review = EvidenceReview(
        session_id=target.session_id,
        domain=target.domain,
        concept=target.concept,
        previous_outcome=target.outcome,
        new_outcome=new_outcome,  # type: ignore[arg-type] -- validated by pydantic at runtime
        reason=reason,
        reviewer=reviewer,
        timestamp=datetime.now(UTC),
    )
    # If a newer review landed since the caller listed, insert_review
    # raises ValueError (stale) -- but previous_outcome here was just read,
    # so refresh it to the currently effective one first.
    overlay = store.effective_outcomes()
    key = (target.session_id, target.domain.lower(), target.concept.lower())
    if key in overlay:
        review = review.model_copy(update={"previous_outcome": overlay[key][0]})
    store.insert_review(review)
    if review.new_outcome in ("correct", "correct_with_application"):
        store.mark_corrected(review.domain, review.concept, before=review.timestamp)
    return review


def list_observations(
    session_id: str | None = None,
    domain: str | None = None,
) -> list[dict]:
    """Rows for the observations CLI: effective outcome/quality with the
    raw grade alongside whenever a human review overrode it."""
    overlay = store.effective_outcomes()
    rows = []
    for entry in store.query_evidence(session_id=session_id, domain=domain, order_by_recent=True):
        key = (entry.session_id, entry.domain.lower(), entry.concept.lower())
        effective = overlay.get(key)
        rows.append(
            {
                "session_id": entry.session_id,
                "domain": entry.domain,
                "concept": entry.concept,
                "outcome": effective[0] if effective else entry.outcome,
                "quality": effective[1] if effective else entry.quality,
                "graded_outcome": entry.outcome,
                "reviewed": effective is not None,
                "timestamp": entry.timestamp.isoformat(),
            }
        )
    return rows


def _conceptual_understanding(observations: list[_Observation]) -> float:
    """Requires at least one scoring-eligible observation (a mistake, or
    evidence other than "not_reached"). With none, there is nothing for
    this number to say -- callers that can legitimately have no data report
    that absence instead of receiving an invented value (decisions.md #45).
    Internal callers all compute from observations already grouped by
    concept, so they can never hit the empty case; the raise is here to
    keep it that way.

    A weighted average, not a plain one (decisions.md #44): each
    observation's pull on the score is scaled by its own weight
    (confidence for a mistake, quality for evidence), so a low-confidence
    mistake or a low-quality-graded success moves the number less than a
    strong one. This is a real, deliberate change from the old plain
    average even for mistakes-only concepts -- checked against real data
    as part of #44's backfill validation."""
    if not observations:
        raise ValueError("conceptual understanding is undefined with no recorded observations")
    total_weight = sum(o.weight for o in observations)
    if total_weight == 0:
        # Every observation carries zero evidence strength -- fall back to
        # a plain average rather than dividing by zero. Degenerate, but a
        # legal input (confidence/quality of exactly 0.0 is valid).
        return max(0.0, min(1.0, sum(_success_value(o) for o in observations) / len(observations)))
    weighted = sum(_success_value(o) * o.weight for o in observations) / total_weight
    return max(0.0, min(1.0, weighted))


def _success_value(observation: _Observation) -> float:
    if observation.outcome == "incorrect":
        return 1.0 - observation.weight
    if observation.outcome == "partial":
        return 0.5
    return 1.0  # correct, correct_with_application -- capped here, not above 1.0;
    # application's extra rigor earns a bigger *stability* jump instead (see below)


_STABILITY_GROWTH_BY_OUTCOME = {
    "correct_with_application": STABILITY_GROWTH_CORRECT_WITH_APPLICATION,
    "correct": STABILITY_GROWTH_CORRECT,
    "partial": STABILITY_GROWTH_PARTIAL,
}
_DIFFICULTY_DELTA_BY_OUTCOME = {
    "correct_with_application": DIFFICULTY_DELTA_CORRECT_WITH_APPLICATION,
    "correct": DIFFICULTY_DELTA_CORRECT,
    "partial": DIFFICULTY_DELTA_PARTIAL,
    "incorrect": DIFFICULTY_DELTA_INCORRECT,
}


def _fold_stability_difficulty(observations: list[_Observation]) -> tuple[float, float]:
    """Anki-shaped (FSRS semantics, never FSRS's fitted parameters) per-
    concept state, folded chronologically over every observation on every
    call rather than cached in a persisted row -- matches this project's
    existing style (_conceptual_understanding/_overdue_ratio already
    recompute from raw rows every call) and keeps mistakes+evidence as the
    sole source of truth. Cheap at current scale (tens of rows per
    concept); revisit only if that stops being true.

    A later success naturally raises stability on top of whatever an
    earlier failure left behind -- the same way Anki still remembers a past
    lapse after you've since relearned a card. corrected is deliberately
    not read here; it's pure bookkeeping for consumers, not scoring
    input (decisions.md #45's finding about severity/corrected, extended)."""
    stability = INITIAL_STABILITY_DAYS
    difficulty = INITIAL_DIFFICULTY
    for observation in sorted(observations, key=lambda o: o.timestamp):
        if observation.outcome == "incorrect":
            stability *= 1 - STABILITY_DECAY_INCORRECT * observation.weight
        else:
            growth = _STABILITY_GROWTH_BY_OUTCOME[observation.outcome]
            stability *= 1 + (growth - 1) * observation.weight
        difficulty += _DIFFICULTY_DELTA_BY_OUTCOME[observation.outcome] * observation.weight
        difficulty = max(DIFFICULTY_MIN, min(DIFFICULTY_MAX, difficulty))
    return stability, difficulty


def _review_interval_days(stability: float, difficulty: float) -> float:
    """Solves FSRS's own retrievability curve for the elapsed time at which
    predicted recall decays to FSRS_REQUEST_RETENTION, then discounts a bit
    further for difficulty (a harder concept is reviewed sooner than raw
    stability alone suggests, at the same target retention)."""
    raw = stability / FSRS_FACTOR * (FSRS_REQUEST_RETENTION ** (1 / FSRS_DECAY) - 1)
    raw *= 1 - 0.3 * difficulty
    return max(MIN_REVIEW_INTERVAL_DAYS, min(MAX_REVIEW_INTERVAL_DAYS, raw))


def _overdue_ratio(observations: list[_Observation], now: datetime) -> float:
    """>1 means overdue relative to this concept's own interval, <1 means
    not due yet -- exact same shape as before #44 (decisions.md #44 point
    4); only the interval source underneath changed. days_since is rounded
    to the nearest whole day so several observations saved seconds apart in
    the same real session tie instead of getting near-random relative
    ratios from wall-clock noise."""
    stability, difficulty = _fold_stability_difficulty(observations)
    most_recent = max(o.timestamp for o in observations)
    days_since = round((now - most_recent).total_seconds() / 86400)
    return days_since / _review_interval_days(stability, difficulty)


def get_learning_profile(domain: str | None = None) -> list[MasteryEstimate]:
    mistakes_by_key: dict[tuple[str, str], list[MistakeEntry]] = {}
    for mistake in store.query_mistakes(domain=domain):
        mistakes_by_key.setdefault((mistake.domain, mistake.concept), []).append(mistake)

    evidence_by_key: dict[tuple[str, str], list[Evidence]] = {}
    # decisions.md #63: scoring always reads the human-reviewed overlay,
    # so a correction takes effect without editing the immutable raw row.
    for entry in store.query_evidence_effective(domain=domain):
        evidence_by_key.setdefault((entry.domain, entry.concept), []).append(entry)

    # dict.fromkeys, not set() union: preserves first-seen order
    # deterministically, which the downstream ratio/understanding tiebreak
    # sorts (recommend_review_scored, _prioritize_by_importance) depend on
    # for reproducible ordering among exact ties.
    profile = []
    for key in dict.fromkeys(list(mistakes_by_key) + list(evidence_by_key)):
        domain_key, concept = key
        group_mistakes = mistakes_by_key.get(key, [])
        observations = _merge_observations(group_mistakes, evidence_by_key.get(key, []))
        if not observations:
            # Only not_reached evidence exists for this key -- absence, not
            # a tracked concept (decisions.md #44's resolved open question).
            continue
        profile.append(
            MasteryEstimate(
                domain=domain_key,
                concept=concept,
                conceptual_understanding=_conceptual_understanding(observations),
                mistake_count=len(group_mistakes),
                observation_count=len(observations),
            )
        )
    return profile


def estimate_mastery(domain: str, concept: str) -> float | None:
    """None means "no evidence yet" -- nothing scoring-eligible has ever
    been recorded for this concept -- and is deliberately not a score
    (decisions.md #45), now merging both tables (decisions.md #44)."""
    observations = _merge_observations(
        store.query_mistakes(domain=domain, concept=concept),
        store.query_evidence_effective(domain=domain, concept=concept),
    )
    if not observations:
        return None
    return _conceptual_understanding(observations)


def recommend_review_scored(domain: str | None = None) -> list[tuple[str, float]]:
    """Same ranking as recommend_review, with each concept's raw
    _overdue_ratio attached. Groups by concept alone (not domain+concept),
    the same existing quirk get_learning_profile's own grouping doesn't
    share -- preserved as-is, not silently fixed here."""
    mistakes_by_concept: dict[str, list[MistakeEntry]] = {}
    for mistake in store.query_mistakes(domain=domain):
        mistakes_by_concept.setdefault(mistake.concept, []).append(mistake)

    evidence_by_concept: dict[str, list[Evidence]] = {}
    for entry in store.query_evidence_effective(domain=domain):
        evidence_by_concept.setdefault(entry.concept, []).append(entry)

    now = datetime.now(UTC)
    scored = []
    for concept in dict.fromkeys(list(mistakes_by_concept) + list(evidence_by_concept)):
        observations = _merge_observations(mistakes_by_concept.get(concept, []), evidence_by_concept.get(concept, []))
        if not observations:
            continue
        scored.append((concept, _overdue_ratio(observations, now), _conceptual_understanding(observations)))
    scored.sort(key=lambda item: (-item[1], item[2]))
    return [(concept, ratio) for concept, ratio, _ in scored]


def recommend_review(domain: str | None = None) -> list[str]:
    """Ranked by spaced-repetition urgency (`_overdue_ratio`), not just raw
    understanding. Thin wrapper over recommend_review_scored; this
    function's own contract -- list[str], same ordering -- is unchanged."""
    return [concept for concept, _ in recommend_review_scored(domain)]


def recommend_domain() -> str | None:
    """Which domain has gone longest without any tracked activity of either
    kind. `not_reached` evidence counts here (unlike everywhere scoring
    happens): a session that only produced correct/not_reached grades for a
    domain is still real recent activity for rotation purposes, and
    excluding it would make this re-pick that domain too soon after a real,
    successful session.

    `UNTRACKED_DOMAIN` ("general") is excluded from the rotation whenever
    at least one real domain has tracked activity, same as before #44."""
    mistakes = store.query_mistakes()
    evidence = store.query_evidence()
    if not mistakes and not evidence:
        return None

    last_seen: dict[str, datetime] = {}
    for mistake in mistakes:
        current = last_seen.get(mistake.domain)
        if current is None or mistake.timestamp > current:
            last_seen[mistake.domain] = mistake.timestamp
    for entry in evidence:
        current = last_seen.get(entry.domain)
        if current is None or entry.timestamp > current:
            last_seen[entry.domain] = entry.timestamp

    real_domains = {domain: seen for domain, seen in last_seen.items() if domain != UNTRACKED_DOMAIN}
    candidates = real_domains or last_seen
    return min(candidates, key=lambda domain: candidates[domain])
