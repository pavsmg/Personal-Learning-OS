import uuid

import pytest

from learning_os.sessions.service import create_session, finish_session, summarize_session


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")


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


def test_finish_session_not_implemented():
    with pytest.raises(NotImplementedError):
        finish_session("session-1")


def test_summarize_session_not_implemented():
    with pytest.raises(NotImplementedError):
        summarize_session("session-1")
