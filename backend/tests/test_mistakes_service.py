from datetime import UTC, datetime, timedelta

import pytest

from learning_os.mistakes import store
from learning_os.mistakes.models import MistakeEntry
from learning_os.mistakes.service import (
    estimate_mastery,
    get_learning_profile,
    get_recent_mistakes,
    recommend_domain,
    recommend_review,
    recommend_review_scored,
    save_mistake,
    search_mistakes,
)


def insert_mistake_at(concept: str, domain: str, confidence: float, days_ago: float) -> None:
    store.insert_mistake(
        MistakeEntry(
            domain=domain,
            concept=concept,
            explanation="x",
            category="conceptual",
            severity="minor",
            timestamp=datetime.now(UTC) - timedelta(days=days_ago),
            corrected=False,
            confidence=confidence,
            related_notes=[],
        )
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


def test_recommend_review_scored_returns_concept_ratio_pairs_in_recommend_review_order(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    insert_mistake_at("Mostly solid", domain="classical-ml", confidence=0.1, days_ago=5)
    insert_mistake_at("Very shaky", domain="classical-ml", confidence=0.9, days_ago=5)

    scored = recommend_review_scored("classical-ml")

    assert [concept for concept, _ in scored] == recommend_review("classical-ml")
    ratios = [ratio for _, ratio in scored]
    assert ratios == sorted(ratios, reverse=True)


def test_recommend_review_scored_no_data_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert recommend_review_scored() == []


def test_recommend_review_prioritizes_longer_since_last_review_at_equal_understanding(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    insert_mistake_at("Reviewed today", domain="classical-ml", confidence=0.5, days_ago=0)
    insert_mistake_at("Reviewed two weeks ago", domain="classical-ml", confidence=0.5, days_ago=14)

    assert recommend_review("classical-ml") == ["Reviewed two weeks ago", "Reviewed today"]


def test_recommend_review_long_overdue_well_understood_outranks_recent_weak(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    # Well understood (confidence 0.05 -> understanding 0.95, ~13.35-day interval)
    # but last reviewed 20 days ago: overdue_ratio ~= 1.5.
    insert_mistake_at("Well understood, long overdue", domain="classical-ml", confidence=0.05, days_ago=20)
    # Weakly understood (confidence 0.5 -> understanding 0.5, 7.5-day interval)
    # but reviewed yesterday: overdue_ratio ~= 0.13 -- not actually due yet.
    insert_mistake_at("Weak but reviewed yesterday", domain="classical-ml", confidence=0.5, days_ago=1)

    # The old "worst raw understanding first" ranking would have put the
    # weaker concept first regardless of recency -- this is the actual
    # behavioral change spaced-repetition scheduling is supposed to produce.
    assert recommend_review("classical-ml") == ["Well understood, long overdue", "Weak but reviewed yesterday"]


def test_recommend_domain_picks_least_recently_active_domain(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    insert_mistake_at("Touched recently", domain="domain-a", confidence=0.9, days_ago=1)
    insert_mistake_at("Untouched for ages", domain="domain-b", confidence=0.2, days_ago=30)

    assert recommend_domain() == "domain-b"


def test_recommend_domain_uses_each_domains_most_recent_mistake_not_oldest(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    # domain-a's *oldest* entry is old, but it has a fresh one too -- the
    # domain overall is active, so it shouldn't count as the stalest.
    insert_mistake_at("Old, superseded", domain="domain-a", confidence=0.9, days_ago=60)
    insert_mistake_at("Recently reviewed again", domain="domain-a", confidence=0.9, days_ago=1)
    insert_mistake_at("Only touch in weeks", domain="domain-b", confidence=0.2, days_ago=15)

    assert recommend_domain() == "domain-b"


def test_recommend_domain_no_data_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert recommend_domain() is None
