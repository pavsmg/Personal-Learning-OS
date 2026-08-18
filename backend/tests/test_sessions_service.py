import uuid

import pytest

from learning_os.llm_client import LLMReply, ToolCallRequest
from learning_os.sessions.service import (
    _find_blind_spot_topic,
    _prefer_tracked_concepts,
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


class FakeChat:
    """Mirrors test_career_service.py's FakeChat -- never touches the real
    LLM API, records every call it receives for assertions."""

    def __init__(self, reply: LLMReply):
        self._reply = reply
        self.calls: list[dict] = []

    def __call__(self, messages, tools, tool_choice=None):
        self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice})
        return self._reply


def grading_reply(grades: list[dict]) -> LLMReply:
    return LLMReply(
        content=None,
        tool_calls=[ToolCallRequest(id="call_1", name="record_session_grades", arguments={"grades": grades})],
    )


def test_prefer_tracked_concepts_reorders_without_dropping_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.mistakes.service import save_mistake
    from learning_os.retrieval.models import NoteSummary

    save_mistake(
        concept="Zulu", explanation="x", category="conceptual", severity="minor", confidence=0.5, domain="chemistry"
    )
    candidates = [
        NoteSummary(title="Alpha", snippet="", tags=[]),
        NoteSummary(title="Zulu", snippet="", tags=[]),
        NoteSummary(title="Beta", snippet="", tags=[]),
    ]

    result = _prefer_tracked_concepts(candidates, "chemistry")

    assert [note.title for note in result] == ["Zulu", "Alpha", "Beta"]


def test_prefer_tracked_concepts_case_insensitive_match(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.mistakes.service import save_mistake
    from learning_os.retrieval.models import NoteSummary

    save_mistake(
        concept="zulu", explanation="x", category="conceptual", severity="minor", confidence=0.5, domain="chemistry"
    )
    candidates = [NoteSummary(title="Alpha", snippet="", tags=[]), NoteSummary(title="Zulu", snippet="", tags=[])]

    result = _prefer_tracked_concepts(candidates, "chemistry")

    assert [note.title for note in result] == ["Zulu", "Alpha"]


def test_prefer_tracked_concepts_no_tracked_data_is_a_no_op(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.retrieval.models import NoteSummary

    candidates = [NoteSummary(title="Alpha", snippet="", tags=[]), NoteSummary(title="Zulu", snippet="", tags=[])]

    assert _prefer_tracked_concepts(candidates, "chemistry") == candidates


def test_create_session_prefers_tracked_concept_over_untracked_graph_neighbor(tmp_path, monkeypatch):
    """decisions.md #57: among related_notes candidates with no genuine
    urgency gap, one with real tracked evidence in the domain should be
    preferred over an untracked graph neighbor -- the non-language
    counterpart to #31's Turkish-alphabet fix. Without the fix, both
    "Alpha" and "Zulu" tie on importance (nothing links to either) and
    fall back to alphabetical order (Alpha, then Zulu)."""
    write_vault(
        tmp_path,
        {
            "Hub.md": "---\ndomain: chemistry\n---\ncentral concept, linked to [[Alpha]] and [[Zulu]].",
            "Alpha.md": "an untracked related note.",
            "Zulu.md": "a related note with real tracked history.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.mistakes.service import save_mistake

    save_mistake(
        concept="Zulu",
        explanation="x",
        category="conceptual",
        severity="minor",
        confidence=0.5,
        domain="chemistry",
    )

    plan = create_session("Hub", max_concepts=3)

    assert plan.concepts == ["Hub", "Zulu", "Alpha"]


def test_create_session_never_overrides_the_explicitly_requested_anchor(tmp_path, monkeypatch):
    """The anchor is never replaced by tracked-concept preference, even
    when it has no tracked history itself and a related note does --
    unlike _language_concepts, an explicitly-named topic must still show
    up as a concept."""
    write_vault(
        tmp_path,
        {
            "Hub.md": "---\ndomain: chemistry\n---\ncentral concept, linked to [[Zulu]].",
            "Zulu.md": "a related note with real tracked history.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.mistakes.service import save_mistake

    save_mistake(
        concept="Zulu", explanation="x", category="conceptual", severity="minor", confidence=0.5, domain="chemistry"
    )

    plan = create_session("Hub", max_concepts=2)

    assert plan.concepts[0] == "Hub"


def test_create_session_untracked_domain_keeps_original_related_notes_order(tmp_path, monkeypatch):
    """A no-op when nothing in the domain is tracked yet -- absence isn't
    evidence, same honesty as estimate_mastery (#45), not a new problem."""
    write_vault(
        tmp_path,
        {
            "Hub.md": "---\ndomain: chemistry\n---\ncentral concept, linked to [[Alpha]] and [[Zulu]].",
            "Alpha.md": "an untracked related note.",
            "Zulu.md": "another untracked related note.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

    plan = create_session("Hub", max_concepts=3)

    assert plan.concepts == ["Hub", "Alpha", "Zulu"]


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
    assert plan.target_difficulty == "foundational"
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
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    plan = create_session("gradient descent")
    chat = FakeChat(grading_reply([{"concept": c, "outcome": "correct", "quality": 0.9, "rationale": "x"} for c in plan.concepts]))

    finish_session(plan.session_id, _chat_fn=chat)  # should not raise


def test_finish_session_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        finish_session("does-not-exist")


def test_finish_session_records_evidence_from_grading(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    plan = create_session("gradient descent")
    chat = FakeChat(
        grading_reply(
            [{"concept": concept, "outcome": "correct", "quality": 0.9, "rationale": "x"} for concept in plan.concepts]
        )
    )

    finish_session(plan.session_id, _chat_fn=chat)

    from learning_os.mistakes.service import estimate_mastery

    assert estimate_mastery(plan.domain, plan.concepts[0]) == pytest.approx(1.0)


def test_finish_session_is_idempotent(tmp_path, monkeypatch):
    """A second call must not re-grade or duplicate evidence."""
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    plan = create_session("gradient descent")
    chat = FakeChat(
        grading_reply(
            [{"concept": concept, "outcome": "correct", "quality": 0.9, "rationale": "x"} for concept in plan.concepts]
        )
    )

    finish_session(plan.session_id, _chat_fn=chat)
    finish_session(plan.session_id, _chat_fn=chat)  # should not raise, should not re-grade

    assert len(chat.calls) == 1

    from learning_os.mistakes import store

    assert len(store.query_evidence(session_id=plan.session_id)) == len(plan.concepts)


def test_finish_session_swallows_grading_failure(tmp_path, monkeypatch, capsys):
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    plan = create_session("gradient descent")

    def boom(*args, **kwargs):
        raise RuntimeError("model unavailable")

    finish_session(plan.session_id, _chat_fn=boom)  # should not raise

    assert "session grading failed" in capsys.readouterr().err


def test_finish_session_grades_undiscussed_concept_not_reached(tmp_path, monkeypatch):
    """If the grading model's response omits a planned concept entirely,
    it must default to not_reached rather than being silently dropped."""
    write_vault(
        tmp_path,
        {
            "Gradient descent.md": "core optimization concept, linked to [[Optimizer]].",
            "Optimizer.md": "general term for optimization algorithms.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    plan = create_session("gradient descent", max_concepts=2)
    # Only grades the first concept -- omits the rest of the plan.
    chat = FakeChat(
        grading_reply([{"concept": plan.concepts[0], "outcome": "correct", "quality": 0.9, "rationale": "x"}])
    )

    finish_session(plan.session_id, _chat_fn=chat)

    from learning_os.mistakes import store

    outcomes = {e.concept: e.outcome for e in store.query_evidence(session_id=plan.session_id)}
    assert outcomes[plan.concepts[0]] == "correct"
    assert all(outcomes[concept] == "not_reached" for concept in plan.concepts[1:])


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

    # decisions.md #44: a single mistake's stability can only ever shrink
    # from its 1.0-day starting point (an "incorrect" observation never
    # grows it), so its review interval always floors at
    # MIN_REVIEW_INTERVAL_DAYS regardless of confidence -- overdue_ratio
    # reduces to plain days_since. Same confidence and days_ago -> an exact
    # ratio *and* understanding tie, inserted in Leaf-then-Hub order, so
    # without the priority layer Leaf would keep that insertion-order
    # position ahead of Hub. The importance layer must promote Hub (the
    # more central vault concept) past that tie.
    insert_at("Leaf", domain="classical-ml", confidence=0.5, days_ago=5)
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


def test_create_session_target_difficulty_extending_when_all_concepts_settled(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "Gradient descent.md": "---\ndomain: classical-ml\n---\nlinked to [[Optimizer]].",
            "Optimizer.md": "general term for optimization algorithms.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.mistakes.service import save_mistake

    for concept in ("Gradient descent", "Optimizer"):
        save_mistake(
            concept=concept,
            explanation="minor slip",
            category="conceptual",
            severity="minor",
            confidence=0.1,  # understanding 0.9, well above SHAKY_SETTLED_THRESHOLD
            domain="classical-ml",
        )

    plan = create_session("gradient descent", max_concepts=2)

    assert plan.target_difficulty == "extending"


def test_create_session_target_difficulty_consolidating_when_evidence_is_mixed(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "Gradient descent.md": "---\ndomain: classical-ml\n---\nlinked to [[Optimizer]].",
            "Optimizer.md": "general term for optimization algorithms.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from learning_os.mistakes.service import save_mistake

    save_mistake(
        concept="Gradient descent",
        explanation="thought it always converges",
        category="conceptual",
        severity="minor",
        confidence=0.9,  # understanding 0.1, shaky
        domain="classical-ml",
    )
    save_mistake(
        concept="Optimizer",
        explanation="minor slip",
        category="conceptual",
        severity="minor",
        confidence=0.1,  # understanding 0.9, settled
        domain="classical-ml",
    )

    plan = create_session("gradient descent", max_concepts=2)

    assert plan.target_difficulty == "consolidating"


def test_create_session_duration_costs_more_for_shaky_than_settled_concepts(tmp_path, monkeypatch):
    # 4 concepts so the per-class minute totals clear MINIMUM_DURATION_MINUTES
    # (a single concept would floor both scenarios to the same 15-minute
    # minimum and hide the difference this test is checking for).
    write_vault(
        tmp_path,
        {
            "Hub.md": "---\ndomain: classical-ml\n---\nlinked to [[A]], [[B]], [[C]].",
            "A.md": "a",
            "B.md": "b",
            "C.md": "c",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    from learning_os.mistakes.service import save_mistake

    monkeypatch.setenv("DB_PATH", str(tmp_path / "shaky.db"))
    from learning_os.config import get_settings

    get_settings.cache_clear()
    for concept in ("Hub", "A", "B", "C"):
        save_mistake(
            concept=concept,
            explanation="thought it always converges",
            category="conceptual",
            severity="minor",
            confidence=0.9,  # understanding 0.1, shaky
            domain="classical-ml",
        )
    shaky_plan = create_session("Hub", max_concepts=4)

    monkeypatch.setenv("DB_PATH", str(tmp_path / "settled.db"))
    get_settings.cache_clear()
    for concept in ("Hub", "A", "B", "C"):
        save_mistake(
            concept=concept,
            explanation="minor slip",
            category="conceptual",
            severity="minor",
            confidence=0.1,  # understanding 0.9, settled
            domain="classical-ml",
        )
    settled_plan = create_session("Hub", max_concepts=4)

    assert shaky_plan.expected_duration_minutes > settled_plan.expected_duration_minutes
