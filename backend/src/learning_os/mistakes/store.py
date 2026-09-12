import json
import sqlite3
from datetime import datetime

from learning_os.config import get_settings
from learning_os.mistakes import archive
from learning_os.mistakes.models import Evidence, EvidenceReview, MistakeEntry

# decisions.md #63: versioned schema. Fresh databases get the full
# constraints below; databases created before this entry keep their
# existing table definitions (SQLite cannot add CHECKs via ALTER) and
# rely on the pydantic validation enforced on every write path plus the
# UNIQUE index, which *can* be added to an existing table.
SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL CHECK (length(domain) > 0),
    concept TEXT NOT NULL CHECK (length(concept) > 0),
    explanation TEXT NOT NULL CHECK (length(explanation) > 0),
    category TEXT NOT NULL CHECK (length(category) > 0),
    severity TEXT NOT NULL CHECK (length(severity) > 0),
    timestamp TEXT NOT NULL CHECK (length(timestamp) > 0),
    corrected INTEGER NOT NULL CHECK (corrected IN (0, 1)),
    confidence REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    related_notes TEXT NOT NULL
);
"""

# decisions.md #44: additive, not a replacement for `mistakes` -- no
# foreign key between the two, joined at query time by (domain, concept).
EVIDENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL CHECK (length(domain) > 0),
    concept TEXT NOT NULL CHECK (length(concept) > 0),
    timestamp TEXT NOT NULL CHECK (length(timestamp) > 0),
    outcome TEXT NOT NULL CHECK (outcome IN (
        'not_reached', 'incorrect', 'partial', 'correct',
        'correct_with_application')),
    quality REAL NOT NULL CHECK (quality BETWEEN 0.0 AND 1.0),
    source TEXT NOT NULL CHECK (length(source) > 0),
    session_id TEXT NOT NULL CHECK (length(session_id) > 0)
);
"""

# decisions.md #63: one UNIQUE key per graded concept per session, compared
# case-insensitively like every other (domain, concept) lookup in this
# module. Enforced as an index (not inline) so pre-#63 databases gain it
# via migration without a table rebuild. First write wins: a re-grade of
# the same session keeps the original rows (INSERT OR IGNORE).
EVIDENCE_UNIQUE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_session_concept
    ON evidence (session_id, domain COLLATE NOCASE, concept COLLATE NOCASE);
"""

# decisions.md #63: compact session ledger -- plan metadata and grading
# state only, never transcripts (those stay in logs/<session_id>.log,
# outside the database). One row per session, written best-effort by
# sessions/service.py; scoring never reads it, so a missing row degrades
# to "unknown session" rather than wrong math.
SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY CHECK (length(session_id) > 0),
    domain TEXT NOT NULL CHECK (length(domain) > 0),
    objective TEXT NOT NULL,
    concepts_json TEXT NOT NULL,
    started_at TEXT NOT NULL CHECK (length(started_at) > 0),
    finished_at TEXT,
    grading_status TEXT NOT NULL DEFAULT 'pending' CHECK (grading_status IN (
        'pending', 'graded', 'grading_failed')),
    grader_version TEXT NOT NULL DEFAULT ''
);
"""

# decisions.md #63: append-only human corrections of evidence outcomes.
# The evidence row itself is never edited -- the latest review per
# (session_id, domain, concept) wins for scoring, the full history stays
# for audit. Result-only: attribution (domain/concept) is not reviewable.
REVIEWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL CHECK (length(session_id) > 0),
    domain TEXT NOT NULL CHECK (length(domain) > 0),
    concept TEXT NOT NULL CHECK (length(concept) > 0),
    previous_outcome TEXT NOT NULL,
    new_outcome TEXT NOT NULL CHECK (new_outcome IN (
        'not_reached', 'incorrect', 'partial', 'correct',
        'correct_with_application')),
    reason TEXT NOT NULL CHECK (length(reason) > 0),
    reviewer TEXT NOT NULL CHECK (length(reviewer) > 0),
    timestamp TEXT NOT NULL CHECK (length(timestamp) > 0)
);
"""

REVIEWED_QUALITY = 1.0  # a human correction carries full certainty by construction


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent, additive-only migration to SCHEMA_VERSION. Every
    statement is IF NOT EXISTS, so re-running on an already-migrated
    database is a no-op (verified by test)."""
    conn.execute(SCHEMA)
    conn.execute(EVIDENCE_SCHEMA)
    conn.execute(EVIDENCE_UNIQUE_INDEX)
    conn.execute(SESSIONS_SCHEMA)
    conn.execute(REVIEWS_SCHEMA)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _connect() -> sqlite3.Connection:
    db_path = get_settings().db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # decisions.md #63: WAL lets a reader (planner, MCP, backup) proceed
    # while another process writes; busy_timeout turns an instant
    # "database is locked" into a bounded wait instead.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    _migrate(conn)
    return conn


def _row_to_entry(row: sqlite3.Row) -> MistakeEntry:
    return MistakeEntry(
        domain=row["domain"],
        concept=row["concept"],
        explanation=row["explanation"],
        category=row["category"],
        severity=row["severity"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        corrected=bool(row["corrected"]),
        confidence=row["confidence"],
        related_notes=json.loads(row["related_notes"]),
    )


def _row_to_evidence(row: sqlite3.Row) -> Evidence:
    return Evidence(
        domain=row["domain"],
        concept=row["concept"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        outcome=row["outcome"],
        quality=row["quality"],
        source=row["source"],
        session_id=row["session_id"],
    )


def _row_to_review(row: sqlite3.Row) -> EvidenceReview:
    return EvidenceReview(
        session_id=row["session_id"],
        domain=row["domain"],
        concept=row["concept"],
        previous_outcome=row["previous_outcome"],
        new_outcome=row["new_outcome"],
        reason=row["reason"],
        reviewer=row["reviewer"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
    )


def insert_mistake(entry: MistakeEntry) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO mistakes
                (domain, concept, explanation, category, severity, timestamp, corrected, confidence, related_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.domain,
                entry.concept,
                entry.explanation,
                entry.category,
                entry.severity,
                entry.timestamp.isoformat(),
                int(entry.corrected),
                entry.confidence,
                json.dumps(entry.related_notes),
            ),
        )

    # Every write path in the system funnels through here, so this is the one
    # place the export and backups can be kept honest (decisions.md #46).
    archive.after_write(query_mistakes(), get_settings().db_path)


def query_mistakes(
    *,
    concept: str | None = None,
    domain: str | None = None,
    text: str | None = None,
    limit: int | None = None,
    order_by_recent: bool = False,
) -> list[MistakeEntry]:
    clauses = []
    params: list[object] = []

    if concept is not None:
        clauses.append("concept = ? COLLATE NOCASE")
        params.append(concept)
    if domain is not None:
        clauses.append("domain = ? COLLATE NOCASE")
        params.append(domain)
    if text is not None:
        clauses.append("(concept LIKE ? OR explanation LIKE ?)")
        params.extend([f"%{text}%", f"%{text}%"])

    query = "SELECT * FROM mistakes"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    if order_by_recent:
        query += " ORDER BY timestamp DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    return [_row_to_entry(row) for row in rows]


def insert_evidence(entry: Evidence) -> None:
    """Single-row write path (tests, backfill helpers). The live session
    path uses save_session_evidence below so a session's rows land
    atomically; both enforce the same UNIQUE key, so a duplicate raises
    here (fail fast) while the session path ignores it (idempotent)."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO evidence
                (domain, concept, timestamp, outcome, quality, source, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.domain,
                entry.concept,
                entry.timestamp.isoformat(),
                entry.outcome,
                entry.quality,
                entry.source,
                entry.session_id,
            ),
        )

    archive.after_evidence_write(query_evidence(), get_settings().db_path)


def save_session_evidence(entries: list[Evidence]) -> dict[str, int]:
    """decisions.md #63: the atomic, idempotent write path for one
    session's graded evidence. All inserts plus their `corrected` flips
    commit in a single transaction -- a crash mid-session can no longer
    leave half a session graded. Re-running for the same session inserts
    nothing new (UNIQUE key, first write wins) and re-applies already-
    satisfied flips as no-ops. Returns row counts for observability."""
    if not entries:
        return {"inserted": 0, "corrected": 0}
    db_path = get_settings().db_path
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        before = conn.total_changes
        for entry in entries:
            conn.execute(
                """
                INSERT OR IGNORE INTO evidence
                    (domain, concept, timestamp, outcome, quality, source, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.domain,
                    entry.concept,
                    entry.timestamp.isoformat(),
                    entry.outcome,
                    entry.quality,
                    entry.source,
                    entry.session_id,
                ),
            )
        inserted = conn.total_changes - before
        corrected = 0
        for entry in entries:
            if entry.outcome in ("correct", "correct_with_application"):
                cursor = conn.execute(
                    """
                    UPDATE mistakes SET corrected = 1
                    WHERE domain = ? COLLATE NOCASE
                      AND concept = ? COLLATE NOCASE
                      AND corrected = 0
                      AND timestamp <= ?
                    """,
                    (entry.domain, entry.concept, entry.timestamp.isoformat()),
                )
                corrected += cursor.rowcount

    stats = {"inserted": inserted, "corrected": corrected}
    archive.after_evidence_write(query_evidence(), db_path)
    if corrected:
        archive.after_write(query_mistakes(), db_path)
    return stats


def query_evidence(
    *,
    concept: str | None = None,
    domain: str | None = None,
    session_id: str | None = None,
    limit: int | None = None,
    order_by_recent: bool = False,
) -> list[Evidence]:
    """Raw graded rows, exactly as the grader wrote them -- the immutable
    source of truth. Scoring and display use query_evidence_effective,
    which overlays human reviews."""
    clauses = []
    params: list[object] = []

    if concept is not None:
        clauses.append("concept = ? COLLATE NOCASE")
        params.append(concept)
    if domain is not None:
        clauses.append("domain = ? COLLATE NOCASE")
        params.append(domain)
    if session_id is not None:
        clauses.append("session_id = ?")
        params.append(session_id)

    query = "SELECT * FROM evidence"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    if order_by_recent:
        query += " ORDER BY timestamp DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    return [_row_to_evidence(row) for row in rows]


def query_reviews(
    *,
    session_id: str | None = None,
    domain: str | None = None,
    concept: str | None = None,
) -> list[EvidenceReview]:
    """Full review history, oldest first -- audit trail, not scoring
    input. Scoring reads only the latest review per key (see
    effective_outcomes)."""
    clauses = []
    params: list[object] = []
    if session_id is not None:
        clauses.append("session_id = ?")
        params.append(session_id)
    if domain is not None:
        clauses.append("domain = ? COLLATE NOCASE")
        params.append(domain)
    if concept is not None:
        clauses.append("concept = ? COLLATE NOCASE")
        params.append(concept)

    query = "SELECT * FROM evidence_reviews"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY timestamp ASC, id ASC"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_review(row) for row in rows]


def effective_outcomes() -> dict[tuple[str, str, str], tuple[str, float]]:
    """Latest human review per (session_id, domain, concept), as
    (new_outcome, REVIEWED_QUALITY) -- the scoring-overlay map. Keys use
    the stored session_id verbatim, domain/concept lowercased (matching
    the UNIQUE index's NOCASE semantics)."""
    effective: dict[tuple[str, str, str], tuple[str, float]] = {}
    for review in query_reviews():
        effective[(review.session_id, review.domain.lower(), review.concept.lower())] = (
            review.new_outcome,
            REVIEWED_QUALITY,
        )
    return effective


def query_evidence_effective(
    *,
    concept: str | None = None,
    domain: str | None = None,
    session_id: str | None = None,
    limit: int | None = None,
    order_by_recent: bool = False,
) -> list[Evidence]:
    """Graded rows with the latest human review overlaid (same filters as
    query_evidence). This is what scoring, the CLI, and exports display;
    query_evidence stays raw for audit."""
    overlay = effective_outcomes()
    reviewed = []
    for entry in query_evidence(
        concept=concept,
        domain=domain,
        session_id=session_id,
        limit=limit,
        order_by_recent=order_by_recent,
    ):
        key = (entry.session_id, entry.domain.lower(), entry.concept.lower())
        if key in overlay:
            outcome, quality = overlay[key]
            reviewed.append(entry.model_copy(update={"outcome": outcome, "quality": quality}))
        else:
            reviewed.append(entry)
    return reviewed


def insert_review(review: EvidenceReview) -> None:
    """Appends one human correction. Fails fast when the referenced
    evidence row does not exist, or when `previous_outcome` no longer
    matches the currently effective outcome (stale correction based on an
    outdated listing) -- the caller must re-list and re-confirm."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT outcome FROM evidence
            WHERE session_id = ?
              AND domain = ? COLLATE NOCASE
              AND concept = ? COLLATE NOCASE
            """,
            (review.session_id, review.domain, review.concept),
        ).fetchone()
        if row is None:
            raise KeyError(
                f"No evidence for session={review.session_id!r} "
                f"domain={review.domain!r} concept={review.concept!r}"
            )
        latest = conn.execute(
            """
            SELECT new_outcome FROM evidence_reviews
            WHERE session_id = ?
              AND domain = ? COLLATE NOCASE
              AND concept = ? COLLATE NOCASE
            ORDER BY timestamp DESC, id DESC LIMIT 1
            """,
            (review.session_id, review.domain, review.concept),
        ).fetchone()
        current = latest["new_outcome"] if latest is not None else row["outcome"]
        if current != review.previous_outcome:
            raise ValueError(
                f"Stale correction: {review.concept!r} is currently "
                f"{current!r}, not {review.previous_outcome!r} -- re-list and confirm."
            )
        conn.execute(
            """
            INSERT INTO evidence_reviews
                (session_id, domain, concept, previous_outcome, new_outcome,
                 reason, reviewer, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review.session_id,
                review.domain,
                review.concept,
                review.previous_outcome,
                review.new_outcome,
                review.reason,
                review.reviewer,
                review.timestamp.isoformat(),
            ),
        )

    archive.after_reviews_write(query_reviews(), get_settings().db_path)


def mark_corrected(domain: str, concept: str, before: datetime) -> int:
    """Flips corrected=True on mistakes rows for (domain, concept) recorded
    at or before `before` -- decisions.md #44 point 6. Re-runs the mistakes
    archive hook since this mutates rows already committed there."""
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE mistakes SET corrected = 1
            WHERE domain = ? COLLATE NOCASE
              AND concept = ? COLLATE NOCASE
              AND corrected = 0
              AND timestamp <= ?
            """,
            (domain, concept, before.isoformat()),
        )
        affected = cursor.rowcount

    if affected:
        archive.after_write(query_mistakes(), get_settings().db_path)
    return affected


def save_session(
    session_id: str,
    domain: str,
    objective: str,
    concepts: list[str],
    started_at: datetime,
    grader_version: str = "",
) -> None:
    """Best-effort ledger write for a new session plan. INSERT OR IGNORE:
    a retried create with the same id keeps the original row."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO sessions
                (session_id, domain, objective, concepts_json, started_at,
                 grading_status, grader_version)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (session_id, domain, objective, json.dumps(concepts), started_at.isoformat(), grader_version),
        )


def mark_session(session_id: str, finished_at: datetime, grading_status: str) -> None:
    """Records session teardown state. Unknown ids are ignored (the
    ledger is observability, never load-bearing for scoring)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET finished_at = ?, grading_status = ? WHERE session_id = ?",
            (finished_at.isoformat(), grading_status, session_id),
        )


def query_sessions(session_id: str | None = None) -> list[dict]:
    """Ledger rows for inspection/debugging. Plain dicts, not models --
    this table is observability, not the scoring contract."""
    with _connect() as conn:
        if session_id is not None:
            rows = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sessions ORDER BY started_at DESC").fetchall()
    return [dict(row) | {"concepts": json.loads(row["concepts_json"])} for row in rows]
