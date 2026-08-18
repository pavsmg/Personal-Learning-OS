import json
import sqlite3
from datetime import datetime

from learning_os.config import get_settings
from learning_os.mistakes import archive
from learning_os.mistakes.models import Evidence, MistakeEntry

SCHEMA = """
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    concept TEXT NOT NULL,
    explanation TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    corrected INTEGER NOT NULL,
    confidence REAL NOT NULL,
    related_notes TEXT NOT NULL
);
"""

# decisions.md #44: additive, not a replacement for `mistakes` -- no
# foreign key between the two, joined at query time by (domain, concept).
EVIDENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    concept TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    outcome TEXT NOT NULL,
    quality REAL NOT NULL,
    source TEXT NOT NULL,
    session_id TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    db_path = get_settings().db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.execute(EVIDENCE_SCHEMA)
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


def query_evidence(
    *,
    concept: str | None = None,
    domain: str | None = None,
    session_id: str | None = None,
    limit: int | None = None,
    order_by_recent: bool = False,
) -> list[Evidence]:
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
