import pytest

from learning_os.mistakes.service import (
    estimate_mastery,
    get_learning_profile,
    get_recent_mistakes,
    recommend_review,
    save_mistake,
    search_mistakes,
)


def test_save_mistake_persists_and_returns_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    entry = save_mistake(
        concept="Gradient descent",
        explanation="Thought it moves toward higher loss.",
        category="conceptual",
        severity="minor",
        confidence=0.7,
        domain="classical-ml",
    )

    assert entry.concept == "Gradient descent"
    assert entry.domain == "classical-ml"
    assert entry.corrected is False
    assert get_recent_mistakes(domain="classical-ml") == [entry]


def test_search_mistakes_matches_text(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Gradient descent",
        explanation="mixed up the sign of the update",
        category="conceptual",
        severity="minor",
        confidence=0.6,
        domain="classical-ml",
    )
    save_mistake(
        concept="Vowel Harmony",
        explanation="thought suffix vowels were fixed",
        category="conceptual",
        severity="minor",
        confidence=0.6,
        domain="languages",
    )

    results = search_mistakes("sign")

    assert [r.concept for r in results] == ["Gradient descent"]


def test_get_recent_mistakes_filters_by_domain(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Gradient descent",
        explanation="x",
        category="conceptual",
        severity="minor",
        confidence=0.5,
        domain="classical-ml",
    )
    save_mistake(
        concept="Vowel Harmony",
        explanation="y",
        category="conceptual",
        severity="minor",
        confidence=0.5,
        domain="languages",
    )

    results = get_recent_mistakes(domain="languages")

    assert [r.concept for r in results] == ["Vowel Harmony"]


def test_estimate_mastery_default_with_no_mistakes(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert estimate_mastery("classical-ml", "Gradient descent") == 1.0


def test_estimate_mastery_reflects_recorded_mistakes(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Gradient descent",
        explanation="x",
        category="conceptual",
        severity="major",
        confidence=0.9,
        domain="classical-ml",
    )

    result = estimate_mastery("classical-ml", "Gradient descent")

    assert result == pytest.approx(0.1)  # 1.0 - average confidence (0.9)


def test_get_learning_profile_aggregates_with_mistake_count(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Gradient descent",
        explanation="x",
        category="conceptual",
        severity="minor",
        confidence=0.4,
        domain="classical-ml",
    )
    save_mistake(
        concept="Gradient descent",
        explanation="y",
        category="conceptual",
        severity="minor",
        confidence=0.6,
        domain="classical-ml",
    )

    profile = get_learning_profile("classical-ml")

    assert len(profile) == 1
    assert profile[0].concept == "Gradient descent"
    assert profile[0].mistake_count == 2
    assert profile[0].conceptual_understanding == pytest.approx(0.5)  # 1.0 - avg(0.4, 0.6)


def test_get_learning_profile_empty_domain_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert get_learning_profile("classical-ml") == []


def test_get_learning_profile_no_domain_aggregates_across_all_domains(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Gradient descent",
        explanation="x",
        category="conceptual",
        severity="minor",
        confidence=0.4,
        domain="classical-ml",
    )
    save_mistake(
        concept="Vowel Harmony",
        explanation="y",
        category="conceptual",
        severity="minor",
        confidence=0.2,
        domain="languages",
    )

    profile = get_learning_profile()

    assert {(p.domain, p.concept) for p in profile} == {
        ("classical-ml", "Gradient descent"),
        ("languages", "Vowel Harmony"),
    }


def test_get_learning_profile_groups_same_concept_name_by_domain_separately(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Overfitting",
        explanation="ml sense",
        category="conceptual",
        severity="minor",
        confidence=0.3,
        domain="classical-ml",
    )
    save_mistake(
        concept="Overfitting",
        explanation="stats sense",
        category="conceptual",
        severity="minor",
        confidence=0.5,
        domain="statistics",
    )

    profile = get_learning_profile()

    assert len(profile) == 2
    assert all(p.mistake_count == 1 for p in profile)


def test_recommend_review_sorts_worst_first(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Mostly solid",
        explanation="x",
        category="conceptual",
        severity="minor",
        confidence=0.1,
        domain="classical-ml",
    )
    save_mistake(
        concept="Very shaky",
        explanation="y",
        category="conceptual",
        severity="major",
        confidence=0.9,
        domain="classical-ml",
    )

    assert recommend_review("classical-ml") == ["Very shaky", "Mostly solid"]


def test_recommend_review_no_data_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert recommend_review() == []
