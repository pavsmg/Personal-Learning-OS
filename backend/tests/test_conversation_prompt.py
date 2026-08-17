from learning_os.conversation.prompt import build_system_prompt
from learning_os.sessions.models import SessionPlan


def make_plan(target_difficulty: str) -> SessionPlan:
    return SessionPlan(
        session_id="test-session",
        domain="classical-ml",
        objective="Review Gradient descent and related concepts",
        concepts=["Gradient descent", "Optimizer"],
        target_difficulty=target_difficulty,
        expected_duration_minutes=15,
    )


def test_build_system_prompt_states_starting_point_for_foundational():
    prompt = build_system_prompt(make_plan("foundational"))

    assert "Starting point: foundational" in prompt
    assert "Open from mechanism and definitions" in prompt


def test_build_system_prompt_states_starting_point_for_extending():
    prompt = build_system_prompt(make_plan("extending"))

    assert "Starting point: extending" in prompt
    assert "Skip the definitions" in prompt


def test_build_system_prompt_does_not_mention_duration():
    prompt = build_system_prompt(make_plan("foundational"))

    assert "expected_duration_minutes" not in prompt
    assert "15 minutes" not in prompt
