"""decisions.md #63: versioned schema, atomic session writes, idempotency,
validation, compact session ledger, and human reviews -- all offline."""

import json
import sqlite3
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from learning_os.mistakes import (
    archive,
    list_observations,
    record_evidence,
    record_evidence_review,
    save_mistake,
    store,
)
from learning_os.mistakes.models import Evidence, EvidenceReview, MistakeEntry


def _evidence(session_id="s1", domain="physics", concept="Force", outcome="incorrect", quality=0.8):
    return Evidence(
        domain=domain,
        concept=concept,
        timestamp=datetime.now(UTC),
        outcome=outcome,
        quality=quality,
        source="session_grading",
        session_id=session_id,
    )


def test_migration_sets_schema_version_and_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    store.insert_mistake(
        MistakeEntry(
            domain="d",
            concept="c",
            explanation="x",
            category="conceptual",
            severity="minor",
            timestamp=datetime.now(UTC),
            corrected=False,
            confidence=0.5,
            related_notes=[],
        )
    )
    # Second connection re-runs the migration on the existing database.
    store.insert_mistake(
        MistakeEntry(
            domain="d",
            concept="c2",
            explanation="y",
            category="conceptual",
            severity="minor",
            timestamp=datetime.now(UTC),
            corrected=False,
            confidence=0.5,
            related_notes=[],
        )
    )

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == store.SCHEMA_VERSION
        index = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'idx_evidence_session_concept'"
        ).fetchone()
        assert index is not None and "UNIQUE" in index[0].upper()
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert {"mistakes", "evidence", "sessions", "evidence_reviews"} <= tables
    finally:
        conn.close()
    assert len(store.query_mistakes()) == 2


def test_models_reject_out_of_range_and_empty_values():
    with pytest.raises(ValidationError):
        _evidence(quality=1.5)
    with pytest.raises(ValidationError):
        _evidence(quality=-0.1)
    with pytest.raises(ValidationError):
        _evidence(domain="")
    with pytest.raises(ValidationError):
        MistakeEntry(
            domain="d",
            concept="c",
            explanation="x",
            category="conceptual",
            severity="minor",
            timestamp=datetime.now(UTC),
            corrected=False,
            confidence=2.0,
            related_notes=[],
        )
    with pytest.raises(ValidationError):
        EvidenceReview(
            session_id="s",
            domain="d",
            concept="c",
            previous_outcome="incorrect",
            new_outcome="correct",
            reason="",
            reviewer="human",
            timestamp=datetime.now(UTC),
        )


def test_save_session_evidence_is_atomic_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Force",
        explanation="thought force needs motion",
        category="conceptual",
        severity="minor",
        confidence=0.9,
        domain="physics",
    )
    entries = [
        _evidence(concept="Force", outcome="correct", quality=0.9),
        _evidence(concept="Energy", outcome="partial", quality=0.6),
    ]

    first = record_evidence(entries)
    assert first == {"inserted": 2, "corrected": 1}
    assert store.query_mistakes(concept="Force")[0].corrected is True

    # Re-running the same session inserts nothing and flips nothing new.
    second = record_evidence(entries)
    assert second == {"inserted": 0, "corrected": 0}
    assert len(store.query_evidence(session_id="s1")) == 2


def test_single_insert_evidence_fails_fast_on_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    store.insert_evidence(_evidence())
    with pytest.raises(sqlite3.IntegrityError):
        store.insert_evidence(_evidence())


def test_explanation_is_truncated_to_short_summary(tmp_path, monkeypatch):
    from learning_os.mistakes.service import MAX_EXPLANATION_CHARS

    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    entry = save_mistake(
        concept="Force",
        explanation="x" * (MAX_EXPLANATION_CHARS + 100),
        category="conceptual",
        severity="minor",
        confidence=0.5,
        domain="physics",
    )

    assert len(entry.explanation) == MAX_EXPLANATION_CHARS
    assert len(store.query_mistakes()[0].explanation) == MAX_EXPLANATION_CHARS


def test_review_overrides_scoring_without_editing_raw_row(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    from learning_os.mistakes import estimate_mastery

    record_evidence([_evidence(outcome="incorrect", quality=0.9)])
    before = estimate_mastery("physics", "Force")

    review = record_evidence_review(
        session_id="s1", concept="Force", new_outcome="correct", reason="learner actually derived it"
    )
    assert review.previous_outcome == "incorrect"

    after = estimate_mastery("physics", "Force")
    assert after is not None and before is not None and after > before
    # Raw row untouched; overlay carries the correction.
    assert store.query_evidence()[0].outcome == "incorrect"
    assert store.query_evidence_effective()[0].outcome == "correct"
    assert store.query_evidence_effective()[0].quality == store.REVIEWED_QUALITY


def test_review_history_is_append_only_latest_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    record_evidence([_evidence(outcome="incorrect", quality=0.9)])
    record_evidence_review(session_id="s1", concept="Force", new_outcome="partial", reason="half right")
    record_evidence_review(session_id="s1", concept="force", new_outcome="correct", reason="re-checked log")

    history = store.query_reviews(session_id="s1")
    assert [r.new_outcome for r in history] == ["partial", "correct"]
    assert store.query_evidence_effective()[0].outcome == "correct"


def test_review_rejects_unknown_and_stale_corrections(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    with pytest.raises(KeyError):
        record_evidence_review(session_id="nope", concept="Force", new_outcome="correct", reason="x")

    record_evidence([_evidence(outcome="incorrect", quality=0.9)])
    stale = EvidenceReview(
        session_id="s1",
        domain="physics",
        concept="Force",
        previous_outcome="correct",  # wrong: currently incorrect
        new_outcome="partial",
        reason="stale",
        reviewer="human",
        timestamp=datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="Stale correction"):
        store.insert_review(stale)


def test_review_requires_domain_when_concept_is_ambiguous(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    record_evidence([_evidence(domain="physics"), _evidence(domain="chemistry")])
    with pytest.raises(ValueError, match="--domain"):
        record_evidence_review(session_id="s1", concept="Force", new_outcome="correct", reason="x")
    review = record_evidence_review(
        session_id="s1", concept="Force", new_outcome="correct", reason="x", domain="chemistry"
    )
    assert review.domain == "chemistry"


def test_review_to_correct_flips_matching_mistakes(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    save_mistake(
        concept="Force",
        explanation="x",
        category="conceptual",
        severity="minor",
        confidence=0.9,
        domain="physics",
    )
    record_evidence([_evidence(outcome="incorrect", quality=0.9)])
    assert store.query_mistakes()[0].corrected is False

    record_evidence_review(session_id="s1", concept="Force", new_outcome="correct", reason="verified")
    assert store.query_mistakes()[0].corrected is True


def test_list_observations_shows_effective_outcome(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    record_evidence([_evidence(outcome="incorrect", quality=0.9)])
    record_evidence_review(session_id="s1", concept="Force", new_outcome="partial", reason="half")
    rows = list_observations(session_id="s1")
    assert rows[0]["outcome"] == "partial"
    assert rows[0]["graded_outcome"] == "incorrect"
    assert rows[0]["reviewed"] is True


def test_session_ledger_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    store.save_session("sess-1", "physics", "Review Force", ["Force"], datetime.now(UTC))
    store.save_session("sess-1", "physics", "Review Force", ["Force"], datetime.now(UTC))  # retry: no-op
    store.mark_session("sess-1", datetime.now(UTC), "graded")

    rows = store.query_sessions("sess-1")
    assert len(rows) == 1
    assert rows[0]["grading_status"] == "graded"
    assert rows[0]["concepts"] == ["Force"]


def test_session_lifecycle_is_recorded_in_the_ledger(tmp_path, monkeypatch):
    """create_session writes a pending ledger row; finish_session marks it
    graded -- both best-effort, both verified here against a tmp vault."""
    from learning_os.llm_client import LLMReply, ToolCallRequest
    from learning_os.sessions.service import create_session, finish_session

    (tmp_path / "Gradient descent.md").write_text("core optimization concept.", encoding="utf-8")
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

    plan = create_session("gradient descent")
    pending = store.query_sessions(plan.session_id)[0]
    assert pending["grading_status"] == "pending"
    assert pending["concepts"] == plan.concepts

    chat = lambda messages, tools, tool_choice=None: LLMReply(  # noqa: E731 -- test fake
        content=None,
        tool_calls=[
            ToolCallRequest(
                id="call_1",
                name="record_session_grades",
                arguments={
                    "grades": [
                        {"concept": c, "outcome": "correct", "quality": 0.9, "rationale": "x"}
                        for c in plan.concepts
                    ]
                },
            )
        ],
    )
    finish_session(plan.session_id, _chat_fn=chat)
    assert store.query_sessions(plan.session_id)[0]["grading_status"] == "graded"
    assert len(store.query_evidence(session_id=plan.session_id)) == len(plan.concepts)


def test_reviews_export_round_trips_and_backup_refreshes_all(tmp_path, monkeypatch):
    from learning_os.mistakes import cli

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    record_evidence([_evidence(outcome="incorrect", quality=0.9)])
    record_evidence_review(session_id="s1", concept="Force", new_outcome="correct", reason="verified")

    monkeypatch.setattr("sys.argv", ["learning-os-backup", "--export-only"])
    cli.run()

    exported = json.loads(archive.reviews_export_path(db_path).read_text(encoding="utf-8"))
    assert len(exported) == 1
    assert exported[0]["new_outcome"] == "correct"
    assert json.loads(archive.evidence_export_path(db_path).read_text(encoding="utf-8"))[0]["outcome"] == (
        "incorrect"
    )
