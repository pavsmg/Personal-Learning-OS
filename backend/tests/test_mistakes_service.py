from datetime import UTC, datetime, timedelta

import pytest

from learning_os.mistakes import store
from learning_os.mistakes.models import Evidence, MistakeEntry
from learning_os.mistakes.service import (
    estimate_mastery,
    get_learning_profile,
    get_recent_mistakes,
    record_evidence,
    recommend_domain,
    recommend_review,
    recommend_review_scored,
    save_mistake,
    search_mistakes,
)


def insert_evidence_at(
    concept: str,
    domain: str,
    outcome: str,
    quality: float = 0.9,
    days_ago: float = 0,
    session_id: str = "session-1",
) -> None:
    store.insert_evidence(
        Evidence(
            domain=domain,
            concept=concept,
            timestamp=datetime.now(UTC) - timedelta(days=days_ago),
            outcome=outcome,
            quality=quality,
            source="session_grading",
            session_id=session_id,
        )
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


def test_estimate_mastery_reports_absence_with_no_mistakes(tmp_path, monkeypatch):
    """No evidence is reported as absence, not as a score -- 1.0 read as
    "fully understood" and 0.0 would rank a never-seen concept below a
    demonstrably failed one (decisions.md #45)."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert estimate_mastery("classical-ml", "Gradient descent") is None


def test_estimate_mastery_absence_is_distinct_from_a_low_score(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Gradient descent",
        explanation="x",
        category="conceptual",
        severity="major",
        confidence=1.0,
        domain="classical-ml",
    )

    tracked_and_worst_possible = estimate_mastery("classical-ml", "Gradient descent")

    assert tracked_and_worst_possible == 0.0
    assert estimate_mastery("classical-ml", "Backpropagation") is None


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
    assert profile[0].observation_count == 2
    # decisions.md #44: a *weighted* average, not a plain one -- each
    # mistake's pull on the score is scaled by its own confidence. Values
    # are (1-0.4)=0.6 weighted 0.4, and (1-0.6)=0.4 weighted 0.6:
    # (0.6*0.4 + 0.4*0.6) / (0.4+0.6) = 0.48, not the old plain 0.5.
    assert profile[0].conceptual_understanding == pytest.approx(0.48)


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


def test_recommend_domain_skips_general_when_a_real_domain_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    # "general" is the stalest domain by raw last-seen date, but it's not a
    # domain anyone chose -- a real domain, even a more recently active one,
    # should still win the rotation.
    insert_mistake_at("Untagged note mistake", domain="general", confidence=0.5, days_ago=30)
    insert_mistake_at("Real domain mistake", domain="classical-ml", confidence=0.5, days_ago=1)

    assert recommend_domain() == "classical-ml"


def test_recommend_domain_returns_general_when_it_is_the_only_domain_tracked(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    insert_mistake_at("Only tracked mistake", domain="general", confidence=0.5, days_ago=5)

    assert recommend_domain() == "general"


# --- decisions.md #44: two-sided evidence ---


def test_evidence_only_concept_is_visible_in_learning_profile(tmp_path, monkeypatch):
    """The actual point of two-sided data: a concept with real evidence but
    zero mistakes must not stay invisible."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    insert_evidence_at("Electromagnetism", domain="physics", outcome="correct", quality=0.95)

    profile = get_learning_profile("physics")

    assert len(profile) == 1
    assert profile[0].concept == "Electromagnetism"
    assert profile[0].mistake_count == 0
    assert profile[0].observation_count == 1
    assert profile[0].conceptual_understanding == pytest.approx(1.0)
    assert estimate_mastery("physics", "Electromagnetism") == pytest.approx(1.0)


def test_not_reached_evidence_does_not_make_a_concept_visible_or_scored(tmp_path, monkeypatch):
    """decisions.md #44's resolved open question: a planned-but-never-quizzed
    concept is recorded (for telemetry) but stays absent for scoring,
    otherwise mere discussion would count as evidence."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    insert_evidence_at("Waves & Optics", domain="physics", outcome="not_reached", quality=0.0)

    assert get_learning_profile("physics") == []
    assert estimate_mastery("physics", "Waves & Optics") is None
    # But it's still on record, not silently dropped.
    assert [e.outcome for e in store.query_evidence(domain="physics")] == ["not_reached"]


def test_record_evidence_flips_corrected_on_matching_mistakes(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Quantum Mechanics",
        explanation="thought it only applies to atoms",
        category="conceptual",
        severity="minor",
        confidence=0.9,
        domain="physics",
    )
    assert get_recent_mistakes(domain="physics")[0].corrected is False

    record_evidence(
        [
            Evidence(
                domain="physics",
                concept="Quantum Mechanics",
                timestamp=datetime.now(UTC),
                outcome="correct_with_application",
                quality=0.92,
                source="session_grading",
                session_id="session-1",
            )
        ]
    )

    assert get_recent_mistakes(domain="physics")[0].corrected is True


def test_record_evidence_does_not_flip_corrected_for_incorrect_or_not_reached(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_mistake(
        concept="Thermodynamics",
        explanation="x",
        category="conceptual",
        severity="minor",
        confidence=0.8,
        domain="physics",
    )

    record_evidence(
        [
            Evidence(
                domain="physics",
                concept="Thermodynamics",
                timestamp=datetime.now(UTC),
                outcome="not_reached",
                quality=0.0,
                source="session_grading",
                session_id="session-1",
            )
        ]
    )

    assert get_recent_mistakes(domain="physics")[0].corrected is False


def test_conceptual_understanding_blends_mistakes_and_later_evidence(tmp_path, monkeypatch):
    """A concept that was once a mistake and later demonstrated correct
    should score higher than the mistake alone -- the actual mechanism
    two-sided evidence exists to provide."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    insert_mistake_at("Electromagnetism", domain="physics", confidence=0.9, days_ago=10)
    mistake_only = estimate_mastery("physics", "Electromagnetism")

    insert_evidence_at("Electromagnetism", domain="physics", outcome="correct", quality=0.9, days_ago=0)
    with_evidence = estimate_mastery("physics", "Electromagnetism")

    assert with_evidence > mistake_only


def test_recommend_domain_counts_not_reached_evidence_as_recent_activity(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    insert_mistake_at("Old mistake", domain="domain-a", confidence=0.5, days_ago=30)
    insert_evidence_at("Recently graded", domain="domain-a", outcome="not_reached", days_ago=1)
    insert_mistake_at("Only touch", domain="domain-b", confidence=0.5, days_ago=15)

    # domain-a's not_reached evidence is more recent than its old mistake,
    # so domain-b (untouched for 15 days) is the stalest domain overall.
    assert recommend_domain() == "domain-b"
