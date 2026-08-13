import re
import uuid
from dataclasses import dataclass, field

from learning_os.language import LANGUAGES, get_curriculum
from learning_os.mistakes import get_learning_profile, recommend_domain, recommend_review_scored
from learning_os.retrieval import concept_importance, get_note, most_important_notes, related_notes, search_notes
from learning_os.retrieval.models import Note
from learning_os.sessions.models import SessionPlan, SessionSummary

DEFAULT_TARGET_DIFFICULTY = "beginner"
DEFAULT_DOMAIN = "general"
MINUTES_PER_CONCEPT = 5
MINIMUM_DURATION_MINUTES = 15
BLIND_SPOT_SCAN_LIMIT = 20
# Naive v1: ratios within the same 0.25-wide band count as "similarly
# overdue," same spirit as MIN/MAX_REVIEW_INTERVAL_DAYS and BM25_K1
# elsewhere -- not tuned against real data, a defensible starting point.
# The real Adam optimizer (1.047) vs Optimizer (0.166) gap, 0.88 apart,
# lands several buckets apart and is correctly left alone.
OVERDUE_TIE_BUCKET_SIZE = 0.25

_LANGUAGE_TITLE_PATTERNS = {language: re.compile(rf"\b{language}\b", re.IGNORECASE) for language in LANGUAGES}


@dataclass
class _SessionRecord:
    plan: SessionPlan
    turns: list[tuple[str, str]] = field(default_factory=list)
    finished: bool = False


_SESSIONS: dict[str, _SessionRecord] = {}


def _infer_domain(note: Note) -> str:
    frontmatter_domain = note.frontmatter.get("domain")
    if frontmatter_domain:
        return str(frontmatter_domain)
    for language, pattern in _LANGUAGE_TITLE_PATTERNS.items():
        if pattern.search(note.title):
            return language
    if note.tags:
        return note.tags[0]
    return DEFAULT_DOMAIN


def _language_concepts(language: str, max_concepts: int) -> list[str]:
    """Real curriculum/practice status for a tracked language, preferred over
    generic vault-note titles: a vault note like "Turkish alphabet" is
    reference material (a letter chart), not a thing to produce or practice,
    and naively anchoring a quiz on it is exactly the wrong shape of question
    for language learning. Returns [] (not an error) when the language has no
    Language-Lab directory or no structured curriculum entries yet — that's
    an honest "nothing tracked" state, not a bug, and the caller falls back
    to the vault heuristic in that case."""
    try:
        curriculum = get_curriculum(language)
    except ValueError:
        return []
    active = [entry for entry in curriculum if not entry.split(" — ", 1)[-1].startswith("Resolved")]
    return (active or curriculum)[:max_concepts]


def _find_blind_spot_topic() -> str | None:
    """A foundational vault concept (highest backlink count) with zero
    tracked mistakes anywhere -- for the automatic-mode cold-start case,
    where recommend_review has nothing to work from yet. Naive in-degree
    centrality (decisions.md #37): the more a note is pointed at, the more
    it's treated as foundational to the vault. Scans the top
    BLIND_SPOT_SCAN_LIMIT most-pointed-at notes for the first one that's
    never been tracked; returns None (not an error) if all of them
    already have tracked history, or the vault has no notes at all --
    the caller falls back to its existing error in that case."""
    tracked = {estimate.concept.lower() for estimate in get_learning_profile()}
    for note in most_important_notes(limit=BLIND_SPOT_SCAN_LIMIT):
        if note.title.lower() not in tracked:
            return note.title
    return None


def _overdue_bucket(ratio: float) -> int:
    return round(ratio / OVERDUE_TIE_BUCKET_SIZE)


def _prioritize_by_importance(ranked: list[tuple[str, float]]) -> list[str]:
    """Layers vault centrality on top of recommend_review_scored's
    urgency ranking. Concepts in the same overdue bucket get re-ranked by
    backlink count; Python's stable sort keeps the original
    urgency/understanding order as the tiebreak beneath that -- including
    for concepts that don't resolve to a vault note at all
    (concept_importance returns 0), which just keep their original
    relative order. A genuine urgency gap (different bucket) is never
    overridden by importance."""
    scored = [(concept, _overdue_bucket(ratio), concept_importance(concept)) for concept, ratio in ranked]
    scored.sort(key=lambda item: (-item[1], -item[2]))
    return [concept for concept, _, _ in scored]


def create_session(topic: str | None = None, max_concepts: int = 5) -> SessionPlan:
    """Naive v1 heuristic: anchor on the best search match, expand via
    related_notes. target_difficulty/expected_duration_minutes are fixed
    defaults for now — mistake/mastery data alone doesn't say how hard a
    session should be or how long it should run.

    Automatic mode (topic=None): the effective topic comes from
    recommend_domain()'s pick — whichever domain has gone longest without
    any tracked activity — filtered through that domain's own
    recommend_review() top pick, rather than the caller naming one. Domain
    first, concept second: without this, one domain with a stubbornly bad
    concept could dominate every automatic session indefinitely, since a
    global top-1 pick has no notion of giving other domains a turn.

    Language domains (`LANGUAGES`) are a deliberate exception to the vault
    anchor+related_notes heuristic: when real curriculum data exists
    (`_language_concepts`), concepts come from there instead, so a session
    is built around what's actually being practiced rather than whatever
    vault note title happened to match the search.

    Cold start (automatic mode, zero mistakes tracked anywhere): rather
    than erroring immediately, falls back to `_find_blind_spot_topic` — a
    foundational, never-tracked vault concept — before giving up.

    Among concepts similarly overdue (`_prioritize_by_importance`), the
    more foundational one (vault backlink count) is preferred — a genuine
    urgency gap is never overridden by this, only a close call is."""
    effective_topic = topic
    is_blind_spot_pick = False
    if effective_topic is None:
        ranked = recommend_review_scored(domain=recommend_domain())
        if ranked:
            effective_topic = _prioritize_by_importance(ranked)[0]
        else:
            blind_spot = _find_blind_spot_topic()
            if blind_spot is None:
                raise ValueError(
                    "No topic given and nothing recommended yet (no mistakes on record) — "
                    "name a topic explicitly."
                )
            effective_topic = blind_spot
            is_blind_spot_pick = True

    matches = search_notes(effective_topic, limit=1)
    if not matches:
        raise ValueError(f"No vault notes found for topic: {effective_topic!r}")

    anchor_title = matches[0].title
    anchor_note = get_note(anchor_title)
    domain = _infer_domain(anchor_note) if anchor_note else DEFAULT_DOMAIN

    concepts = _language_concepts(domain, max_concepts) if domain in LANGUAGES else []
    if concepts:
        objective = (
            f"Practice {domain} (due for review) using tracked curriculum status"
            if topic is None
            else f"Practice {domain} using tracked curriculum status"
        )
    else:
        concepts = [anchor_title]
        for note in related_notes(anchor_title):
            if len(concepts) >= max_concepts:
                break
            concepts.append(note.title)
        objective = (
            f"Review {anchor_title} (due for review) and related concepts"
            if topic is None
            else f"Review {anchor_title} and related concepts"
        )

    if is_blind_spot_pick:
        objective = f"Explore {anchor_title} — a foundational concept not yet reviewed"

    duration = max(MINIMUM_DURATION_MINUTES, MINUTES_PER_CONCEPT * len(concepts))

    plan = SessionPlan(
        session_id=str(uuid.uuid4()),
        domain=domain,
        objective=objective,
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
