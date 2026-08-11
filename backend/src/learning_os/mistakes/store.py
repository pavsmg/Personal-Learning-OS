import json
import sqlite3
from datetime import datetime

from learning_os.config import get_settings
from learning_os.mistakes.models import MistakeEntry

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


def _connect() -> sqlite3.Connection:
    db_path = get_settings().db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
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
