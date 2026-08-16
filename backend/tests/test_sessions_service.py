import uuid

import pytest

from learning_os.sessions.service import (
    _find_blind_spot_topic,
    _prioritize_by_importance,
    create_session,
    finish_session,
    record_turn,
    summarize_session,
)


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_create_session_anchors_on_best_search_match(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "Gradient descent.md": "core optimization concept, linked to [[Optimizer]] and [[Learning rate]].",
            "Optimizer.md": "general term for optimization algorithms.",
            "Learning rate.md": "step size for gradient updates.",
            "Unrelated note.md": "nothing to do with this topic.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    plan = create_session("gradient descent")

    assert plan.concepts[0] == "Gradient descent"
    assert set(plan.concepts[1:]) <= {"Optimizer", "Learning rate"}
    assert "Gradient descent" in plan.objective
    assert plan.target_difficulty == "beginner"
    assert plan.expected_duration_minutes >= 15
    assert uuid.UUID(plan.session_id)


def test_create_session_max_concepts_caps_result(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "Hub.md": "linked to [[A]], [[B]], [[C]], [[D]].",
            "A.md": "a",
            "B.md": "b",
            "C.md": "c",
            "D.md": "d",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    plan = create_session("Hub", max_concepts=2)

    assert len(plan.concepts) == 2
    assert plan.concepts[0] == "Hub"


def test_create_session_raises_when_topic_has_no_match(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Unrelated note.md": "nothing relevant here."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    with pytest.raises(ValueError):
        create_session("xqzzptmnvbklw")


def test_finish_session_marks_known_session_finished(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    plan = create_session("gradient descent")

    finish_session(plan.session_id)  # should not raise


def test_finish_session_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        finish_session("does-not-exist")


def test_record_turn_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        record_turn("does-not-exist", "user", "hello")


def test_summarize_session_reflects_mentioned_concepts(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "Gradient descent.md": "core optimization concept, linked to [[Optimizer]].",
            "Optimizer.md": "general term for optimization algorithms.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    plan = create_session("gradient descent")
    record_turn(plan.session_id, "user", "I think gradient descent just picks random directions.")
    record_turn(plan.session_id, "assistant", "Not quite — gradient descent follows the steepest slope.")

    summary = summarize_session(plan.session_id)

    assert summary.session_id == plan.session_id
    assert "Gradient descent" in summary.concepts_reinforced
    assert "Optimizer" not in summary.concepts_reinforced
    assert "2 exchanges" in summary.summary


def test_summarize_session_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        summarize_session("does-not-exist")


def test_create_session_infers_domain_from_frontmatter(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "---\ndomain: classical-ml\n---\ncore optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    plan = create_session("gradient descent")

    assert plan.domain == "classical-ml"


def test_create_session_infers_domain_from_tag_when_no_frontmatter(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Vowel Harmony.md": "suffix vowels shift to match.\n#languages"})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    plan = create_session("vowel harmony")

    assert plan.domain == "languages"


def test_create_session_defaults_domain_to_general_when_no_signal(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Untagged note.md": "no frontmatter, no tag."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    plan = create_session("untagged note")

    assert plan.domain == "general"


def test_create_session_infers_domain_from_folder_when_no_frontmatter_or_tag(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Chemistry/Periodic Table.md": "no frontmatter, no tag, just filed under a topic folder."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    plan = create_session("periodic table")

    assert plan.domain == "chemistry"


def test_create_session_normalizes_multi_word_folder_name_to_domain(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Signal Processing/Fourier Transform.md": "no frontmatter, no tag."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    plan = create_session("fourier transform")

    assert plan.domain == "signal-processing"


def test_create_session_frontmatter_domain_still_wins_over_folder(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {"Chemistry/Reaction Rate.md": "---\ndomain: kinetics\n---\nfrontmatter should win over the folder name."},
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    plan = create_session("reaction rate")

    assert plan.domain == "kinetics"


def test_create_session_automatic_mode_uses_recommend_review(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {"Gradient descent.md": "---\ndomain: classical-ml\n---\ncore optimization concept."},
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.mistakes.service import save_mistake

    save_mistake(
        concept="Gradient descent",
        explanation="thought it always converges",
        category="conceptual",
        severity="minor",
        confidence=0.7,
        domain="classical-ml",
    )

    plan = create_session(topic=None)

    assert plan.concepts[0] == "Gradient descent"
    assert "due for review" in plan.objective


def test_create_session_automatic_mode_prefers_least_recently_active_domain(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "Frequently reviewed.md": "---\ndomain: domain-a\n---\na concept touched often.",
            "Long neglected.md": "---\ndomain: domain-b\n---\na concept nobody has reviewed in a while.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from datetime import UTC, datetime, timedelta

    from learning_os.mistakes import store
    from learning_os.mistakes.models import MistakeEntry

    def insert_at(concept: str, domain: str, confidence: float, days_ago: float) -> None:
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

    # domain-a's concept has the *higher* raw overdue ratio (short interval,
    # poor understanding) -- pure global ranking would pick this one.
    insert_at("Frequently reviewed", domain="domain-a", confidence=0.9, days_ago=3)
    # domain-b's concept has a lower raw ratio, but domain-b as a whole
    # hasn't been touched in far longer -- this is the case pure
    # global-ratio ranking gets wrong and domain-awareness fixes.
    insert_at("Long neglected", domain="domain-b", confidence=0.2, days_ago=10)

    plan = create_session(topic=None)

    assert plan.domain == "domain-b"
    assert plan.concepts[0] == "Long neglected"


def test_create_session_automatic_mode_raises_when_nothing_recommended(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

    with pytest.raises(ValueError):
        create_session(topic=None)


def test_create_session_automatic_mode_falls_back_to_blind_spot_when_no_mistakes_tracked(tmp_path, monkeypatch):
    # A real vault with a clear hub note, but nothing ever tracked as a
    # mistake yet -- the cold-start case recommend_review alone can't help
    # with. Should pick the most foundational (most-pointed-at) concept
    # instead of erroring outright.
    write_vault(
        tmp_path,
        {
            "Hub.md": "the central concept everything else builds on.",
            "A.md": "builds on [[Hub]].",
            "B.md": "also builds on [[Hub]].",
            "C.md": "also builds on [[Hub]].",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

    plan = create_session(topic=None)

    assert plan.concepts[0] == "Hub"
    assert "foundational" in plan.objective


def test_find_blind_spot_topic_returns_none_when_all_candidates_already_tracked(tmp_path, monkeypatch):
    # Exercises _find_blind_spot_topic directly rather than through
    # create_session: given recommend_domain()/recommend_review() only
    # return empty when the *entire* mistakes table is empty, and
    # _find_blind_spot_topic is only ever reached in exactly that case,
    # its own "already tracked" branch is unreachable through
    # create_session -- real, not a hypothetical, so it needs its own
    # direct test to actually be exercised.
    write_vault(tmp_path, {"Only note.md": "the only thing in this vault."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.mistakes.service import save_mistake

    save_mistake(
        concept="Only note",
        explanation="already tracked",
        category="conceptual",
        severity="minor",
        confidence=0.5,
        domain="general",
    )

    assert _find_blind_spot_topic() is None


def write_hub_and_leaf_vault(tmp_path):
    write_vault(
        tmp_path,
        {
            "Hub.md": "---\ndomain: classical-ml\n---\ncentral concept.",
            "A.md": "builds on [[Hub]].",
            "B.md": "also builds on [[Hub]].",
            "C.md": "also builds on [[Hub]].",
            "Leaf.md": "---\ndomain: classical-ml\n---\nisolated concept, nothing links to it.",
        },
    )


def test_prioritize_by_importance_reorders_close_ratios_by_backlink_count(tmp_path, monkeypatch):
    write_hub_and_leaf_vault(tmp_path)
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    result = _prioritize_by_importance([("Leaf", 0.8), ("Hub", 0.667)])

    assert result == ["Hub", "Leaf"]


def test_prioritize_by_importance_does_not_override_a_genuine_urgency_gap(tmp_path, monkeypatch):
    write_hub_and_leaf_vault(tmp_path)
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    result = _prioritize_by_importance([("Hub", 0.133), ("Leaf", 2.667)])

    assert result == ["Leaf", "Hub"]


def test_prioritize_by_importance_unresolved_concept_gets_zero_importance_and_keeps_relative_order(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    result = _prioritize_by_importance([("Made up A", 1.0), ("Made up B", 0.9)])

    assert result == ["Made up A", "Made up B"]


def test_create_session_automatic_mode_prioritizes_importance_within_overdue_tie(tmp_path, monkeypatch):
    write_hub_and_leaf_vault(tmp_path)
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from datetime import UTC, datetime, timedelta

    from learning_os.mistakes import store
    from learning_os.mistakes.models import MistakeEntry

    def insert_at(concept: str, domain: str, confidence: float, days_ago: float) -> None:
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

    # Same confidence (same 7.5-day interval), close days_ago -> same overdue
    # bucket. Without the priority layer, Leaf (ratio 0.8) would outrank Hub
    # (ratio 0.667) on raw urgency alone.
    insert_at("Leaf", domain="classical-ml", confidence=0.5, days_ago=6)
    insert_at("Hub", domain="classical-ml", confidence=0.5, days_ago=5)

    plan = create_session(topic=None)

    assert plan.concepts[0] == "Hub"


def make_language_lab(tmp_path, language: str, roadmap: str | None = None):
    lang_dir = tmp_path / "language_lab" / "languages" / language
    lang_dir.mkdir(parents=True)
    if roadmap is not None:
        (lang_dir / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    return tmp_path / "language_lab"


def test_create_session_infers_specific_language_domain_from_note_title(tmp_path, monkeypatch):
    write_vault(tmp_path, {"German cases.md": "an accusative, dative, genitive overview.\n#languages"})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LANGUAGE_LAB_PATH", str(tmp_path / "language_lab"))

    plan = create_session("German cases")

    assert plan.domain == "german"


def test_create_session_sources_concepts_from_curriculum_for_tracked_language(tmp_path, monkeypatch):
    write_vault(tmp_path, {"German basics.md": "an entry point note.\n#languages"})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    root = make_language_lab(
        tmp_path,
        "german",
        roadmap="- 1. Cases — In progress\n- 2. Word order — Not started\n- 3. Old habit — Resolved\n",
    )
    monkeypatch.setenv("LANGUAGE_LAB_PATH", str(root))

    plan = create_session("German basics")

    assert plan.domain == "german"
    assert plan.concepts == ["Cases — In progress", "Word order — Not started"]
    assert "curriculum" in plan.objective


def test_create_session_falls_back_to_vault_notes_when_curriculum_empty(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {"German basics.md": "an entry point note, linked to [[Cases]].\n#languages", "Cases.md": "case system."},
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LANGUAGE_LAB_PATH", str(tmp_path / "language_lab"))  # no german dir created

    plan = create_session("German basics")

    assert plan.domain == "german"
    assert plan.concepts[0] == "German basics"
    assert "curriculum" not in plan.objective
