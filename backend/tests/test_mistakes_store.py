from datetime import UTC, datetime

from learning_os.mistakes import store
from learning_os.mistakes.models import Evidence, MistakeEntry


def make_entry(**overrides) -> MistakeEntry:
    defaults = dict(
        domain="classical-ml",
        concept="Gradient descent",
        explanation="Confused direction of descent.",
        category="conceptual",
        severity="minor",
        timestamp=datetime.now(UTC),
        corrected=False,
        confidence=0.8,
        related_notes=["Gradient descent"],
    )
    defaults.update(overrides)
    return MistakeEntry(**defaults)


def make_evidence(**overrides) -> Evidence:
    defaults = dict(
        domain="classical-ml",
        concept="Gradient descent",
        timestamp=datetime.now(UTC),
        outcome="correct",
        quality=0.9,
        source="session_grading",
        session_id="session-1",
    )
    defaults.update(overrides)
    return Evidence(**defaults)


def test_insert_and_query_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    entry = make_entry()

    store.insert_mistake(entry)
    results = store.query_mistakes()

    assert len(results) == 1
    assert results[0].concept == "Gradient descent"
    assert results[0].domain == "classical-ml"
    assert results[0].corrected is False
    assert results[0].related_notes == ["Gradient descent"]


def test_query_filters_by_concept_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    store.insert_mistake(make_entry(concept="Gradient descent"))
    store.insert_mistake(make_entry(concept="Adam optimizer"))

    results = store.query_mistakes(concept="gradient descent")

    assert len(results) == 1
    assert results[0].concept == "Gradient descent"


def test_query_filters_by_domain(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    store.insert_mistake(make_entry(domain="classical-ml"))
    store.insert_mistake(make_entry(domain="languages"))

    results = store.query_mistakes(domain="languages")

    assert len(results) == 1
    assert results[0].domain == "languages"


def test_query_text_search_matches_concept_or_explanation(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    store.insert_mistake(make_entry(concept="Gradient descent", explanation="mixed up the sign"))
    store.insert_mistake(make_entry(concept="Vowel Harmony", explanation="thought suffixes were fixed"))

    results = store.query_mistakes(text="sign")

    assert len(results) == 1
    assert results[0].concept == "Gradient descent"


def test_query_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    for i in range(5):
        store.insert_mistake(make_entry(concept=f"Concept {i}"))

    results = store.query_mistakes(limit=2)

    assert len(results) == 2


def test_query_order_by_recent(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    store.insert_mistake(make_entry(concept="Older", timestamp=datetime(2026, 1, 1, tzinfo=UTC)))
    store.insert_mistake(make_entry(concept="Newer", timestamp=datetime(2026, 6, 1, tzinfo=UTC)))

    results = store.query_mistakes(order_by_recent=True)

    assert [r.concept for r in results] == ["Newer", "Older"]


def test_query_empty_db_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert store.query_mistakes() == []


def test_evidence_insert_and_query_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    entry = make_evidence()

    store.insert_evidence(entry)
    results = store.query_evidence()

    assert len(results) == 1
    assert results[0].concept == "Gradient descent"
    assert results[0].outcome == "correct"
    assert results[0].session_id == "session-1"


def test_evidence_query_filters_by_domain_concept_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    store.insert_evidence(make_evidence(concept="Gradient descent", domain="classical-ml", session_id="s1"))
    store.insert_evidence(make_evidence(concept="Vowel Harmony", domain="languages", session_id="s2"))

    assert [e.concept for e in store.query_evidence(domain="languages")] == ["Vowel Harmony"]
    assert [e.concept for e in store.query_evidence(concept="gradient descent")] == ["Gradient descent"]
    assert [e.concept for e in store.query_evidence(session_id="s2")] == ["Vowel Harmony"]


def test_evidence_query_empty_db_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert store.query_evidence() == []


def test_mark_corrected_flips_only_matching_uncorrected_rows_at_or_before(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    early = datetime(2026, 1, 1, tzinfo=UTC)
    late = datetime(2026, 6, 1, tzinfo=UTC)
    store.insert_mistake(make_entry(concept="Gradient descent", timestamp=early))
    store.insert_mistake(make_entry(concept="Gradient descent", timestamp=late))
    store.insert_mistake(make_entry(concept="Other concept", timestamp=early))

    affected = store.mark_corrected("classical-ml", "gradient descent", before=datetime(2026, 3, 1, tzinfo=UTC))

    assert affected == 1
    by_concept = {(m.concept, m.timestamp): m.corrected for m in store.query_mistakes()}
    assert by_concept[("Gradient descent", early)] is True
    assert by_concept[("Gradient descent", late)] is False
    assert by_concept[("Other concept", early)] is False


def test_mark_corrected_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    store.insert_mistake(make_entry(timestamp=datetime(2026, 1, 1, tzinfo=UTC)))

    first = store.mark_corrected("classical-ml", "Gradient descent", before=datetime(2026, 3, 1, tzinfo=UTC))
    second = store.mark_corrected("classical-ml", "Gradient descent", before=datetime(2026, 3, 1, tzinfo=UTC))

    assert first == 1
    assert second == 0
