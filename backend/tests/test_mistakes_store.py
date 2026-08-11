from datetime import UTC, datetime

from learning_os.mistakes import store
from learning_os.mistakes.models import MistakeEntry


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
