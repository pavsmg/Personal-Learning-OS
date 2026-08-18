import re
import sys
import uuid
from dataclasses import dataclass, field

from learning_os.config import get_settings
from learning_os.language import LANGUAGES, get_curriculum
from learning_os.llm_client import chat_completion
from learning_os.mistakes import get_learning_profile, record_evidence, recommend_domain, recommend_review_scored
from learning_os.retrieval import concept_importance, get_note, most_important_notes, related_notes, search_notes
from learning_os.retrieval.models import Note
from learning_os.session_log import LOG_DIR, SessionLog
from learning_os.sessions.grading import ChatFn, grade_session
from learning_os.sessions.models import SessionPlan, SessionSummary

DEFAULT_TARGET_DIFFICULTY = "foundational"
DEFAULT_DOMAIN = "general"
MINUTES_PER_CONCEPT = 5
MINIMUM_DURATION_MINUTES = 15
BLIND_SPOT_SCAN_LIMIT = 20
# decisions.md #43, v1 constant, not tuned: splits shaky/settled on
# conceptual_understanding. Checked against today's real mistakes.db (10
# tracked pairs): 0.02-0.41 (mostly single wrong-with-high-confidence
# guesses) lands shaky, 0.6-0.85 (single low-confidence slips) lands
# settled, with nothing sitting near the boundary either way. A tie at
# the boundary favors settled -- deeper questioning, not a retreat to
# basics, per pedagogy.md's desirable-difficulty point that smooth
# sessions are the failure mode. Revisit both this and the aggregation
# below (_target_difficulty) once there's enough real evidence per domain
# to tune against instead of reason from a handful of points.
SHAKY_SETTLED_THRESHOLD = 0.5
# Same v1-constant caveat as SHAKY_SETTLED_THRESHOLD: shaky concepts cost
# more session time than settled ones, settled cost less than the
# untracked baseline (MINUTES_PER_CONCEPT) -- direction is principled,
# the exact minutes aren't fit to anything.
MINUTES_SHAKY_CONCEPT = 7
MINUTES_SETTLED_CONCEPT = 3
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


def _domain_from_folder(note: Note) -> str | None:
    """The vault's top-level subfolder a note lives in, e.g. a note under
    Chemistry/... implies domain "chemistry". None for a note directly at
    the vault root (no subfolder) -- most of the vault lives there, and a
    root note gets no folder signal to synthesize a domain from, same as
    if it had no frontmatter/tags."""
    try:
        relative = note.path.relative_to(get_settings().vault_path.resolve())
    except ValueError:
        return None
    if len(relative.parts) < 2:
        return None
    return relative.parts[0].strip().lower().replace(" ", "-")


def infer_domain(note: Note) -> str:
    """Public (not `_`-prefixed) since `classification/service.py` (phase 2
    of decisions.md #49) needs the same resolution logic to find which
    notes already have a real domain to build classifier classes from, and
    which fall to DEFAULT_DOMAIN and are candidates to classify."""
    frontmatter_domain = note.frontmatter.get("domain")
    if frontmatter_domain:
        return str(frontmatter_domain)
    for language, pattern in _LANGUAGE_TITLE_PATTERNS.items():
        if pattern.search(note.title):
            return language
    if note.tags:
        return note.tags[0]
    folder_domain = _domain_from_folder(note)
    if folder_domain:
        return folder_domain
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


def _evidence_classes(domain: str, concepts: list[str]) -> list[str]:
    """Classifies each planned concept as "untracked" (no real mistake
    evidence at all), "shaky", or "settled" (split on conceptual_understanding
    at SHAKY_SETTLED_THRESHOLD) -- decisions.md #43. Case-insensitive lookup,
    same pattern as _find_blind_spot_topic; a concept that doesn't match any
    tracked entry (e.g. a Language-Lab curriculum label with no mistake
    recorded under that exact string) honestly falls to "untracked" rather
    than guessing."""
    profile = {estimate.concept.lower(): estimate for estimate in get_learning_profile(domain=domain)}
    classes = []
    for concept in concepts:
        estimate = profile.get(concept.lower())
        if estimate is None:
            classes.append("untracked")
        elif estimate.conceptual_understanding >= SHAKY_SETTLED_THRESHOLD:
            classes.append("settled")
        else:
            classes.append("shaky")
    return classes


def _target_difficulty(evidence: list[str]) -> str:
    """Session-level depth label from per-concept evidence classes
    (decisions.md #43) -- untracked concepts don't vote either way, since
    absence of evidence isn't evidence of anything. No tracked concepts at
    all keeps today's honest default (foundational); a mix of shaky and
    settled concepts -- the common case once a session has more than one
    or two concepts -- lands on "consolidating" rather than letting either
    extreme dominate."""
    tracked = [evidence_class for evidence_class in evidence if evidence_class != "untracked"]
    if not tracked:
        return DEFAULT_TARGET_DIFFICULTY
    if all(evidence_class == "settled" for evidence_class in tracked):
        return "extending"
    if all(evidence_class == "shaky" for evidence_class in tracked):
        return "foundational"
    return "consolidating"


_MINUTES_BY_EVIDENCE_CLASS = {
    "untracked": MINUTES_PER_CONCEPT,
    "shaky": MINUTES_SHAKY_CONCEPT,
    "settled": MINUTES_SETTLED_CONCEPT,
}


def _expected_duration(evidence: list[str]) -> int:
    """Minutes sized per concept by its evidence class rather than a flat
    rate (decisions.md #43) -- shaky concepts cost more time than settled
    ones. Stays out of the system prompt deliberately (a visible minute
    budget invites clock-watching, which fights rules 2 and 11); this is a
    planning/telemetry value only."""
    return max(MINIMUM_DURATION_MINUTES, sum(_MINUTES_BY_EVIDENCE_CLASS[evidence_class] for evidence_class in evidence))


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
    related_notes. target_difficulty/expected_duration_minutes derive from
    each planned concept's real tracked evidence via _evidence_classes
    (decisions.md #43) -- untracked concepts fall back to today's honest
    default rather than a guess.

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
    domain = infer_domain(anchor_note) if anchor_note else DEFAULT_DOMAIN

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

    evidence = _evidence_classes(domain, concepts)

    plan = SessionPlan(
        session_id=str(uuid.uuid4()),
        domain=domain,
        objective=objective,
        concepts=concepts,
        target_difficulty=_target_difficulty(evidence),
        expected_duration_minutes=_expected_duration(evidence),
    )
    _SESSIONS[plan.session_id] = _SessionRecord(plan=plan)
    return plan


def record_turn(session_id: str, role: str, content: str) -> None:
    _SESSIONS[session_id].turns.append((role, content))


def _session_transcript(session_id: str, record: _SessionRecord) -> str:
    """Prefers the real on-disk logs/<session_id>.log (session_log.py) --
    the shared voice/text format decisions.md #44 is built to read, which
    is what makes voice gradeable too (closing #22 as a side effect).
    Falls back to reconstructing from in-memory turns so finish_session
    stays usable without a real log file, e.g. direct unit tests that
    never go through conversation/loop.py's SessionLog."""
    log_path = LOG_DIR / f"{session_id}.log"
    if log_path.exists():
        return log_path.read_text(encoding="utf-8")
    return "\n".join(f"{role.upper()}: {content}" for role, content in record.turns)


def finish_session(session_id: str, _chat_fn: ChatFn = chat_completion) -> None:
    """Sets finished unconditionally first (unchanged contract), then runs
    decisions.md #44's end-of-session grading pass exactly once per
    session -- the idempotency guard skips grading (no duplicate evidence
    rows or corrected flips) on a second call. Grading is wrapped in a
    swallow-to-stderr, mirroring archive.after_write's precedent: it's
    best-effort enrichment and must not crash session teardown for either
    loop, and stays synchronous (confirmed acceptable for v1 -- matches
    this project's existing LLM-call style, e.g. the career module)."""
    if session_id not in _SESSIONS:
        raise KeyError(f"Unknown session: {session_id}")
    record = _SESSIONS[session_id]
    if record.finished:
        return
    record.finished = True

    log: SessionLog | None = None
    try:
        transcript = _session_transcript(session_id, record)
        log = SessionLog(session_id)
        evidence = grade_session(
            session_id, record.plan.domain, record.plan.concepts, transcript, log=log, _chat_fn=_chat_fn
        )
        record_evidence(evidence)
    except Exception as exc:  # noqa: BLE001 -- grading is best-effort, must not crash session teardown
        print(f"[grading] session grading failed: {exc}", file=sys.stderr)
        if log is not None:
            log.write(f"GRADING FAILED: {exc}")
    finally:
        if log is not None:
            log.close()


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
