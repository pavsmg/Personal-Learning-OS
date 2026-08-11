from learning_os.career.models import JobFitAnalysis
from learning_os.career.service import analyze_job_fit, summarize_skills_for_cv
from learning_os.llm_client import LLMReply, ToolCallRequest
from learning_os.mistakes.service import save_mistake


def set_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))


class FakeChat:
    def __init__(self, reply: LLMReply):
        self._reply = reply
        self.calls: list[dict] = []

    def __call__(self, messages, tools, tool_choice=None):
        self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice})
        return self._reply


def never_called(*args, **kwargs):
    raise AssertionError("chat_fn should not have been called")


def test_summarize_skills_for_cv_no_data_returns_honest_message_without_calling_llm(tmp_path, monkeypatch):
    set_env(monkeypatch, tmp_path)

    result = summarize_skills_for_cv(_chat_fn=never_called)

    assert "Not enough tracked session history" in result


def test_summarize_skills_for_cv_excludes_weak_concepts(tmp_path, monkeypatch):
    set_env(monkeypatch, tmp_path)
    save_mistake(
        concept="Gradient descent",
        explanation="major confusion",
        category="conceptual",
        severity="major",
        confidence=0.9,  # conceptual_understanding = 0.1, below threshold
        domain="classical-ml",
    )

    result = summarize_skills_for_cv(_chat_fn=never_called)

    assert "Not enough tracked session history" in result


def test_summarize_skills_for_cv_calls_llm_with_strengths(tmp_path, monkeypatch):
    set_env(monkeypatch, tmp_path)
    save_mistake(
        concept="Gradient descent",
        explanation="minor slip",
        category="conceptual",
        severity="minor",
        confidence=0.1,  # conceptual_understanding = 0.9, above threshold
        domain="classical-ml",
    )
    chat = FakeChat(LLMReply(content="Solid grasp of gradient descent (classical-ml).", tool_calls=[]))

    result = summarize_skills_for_cv(_chat_fn=chat)

    assert result == "Solid grasp of gradient descent (classical-ml)."
    assert "Gradient descent" in chat.calls[0]["messages"][0]["content"]


def test_analyze_job_fit_forces_tool_choice_and_parses_result(tmp_path, monkeypatch):
    set_env(monkeypatch, tmp_path)
    save_mistake(
        concept="Gradient descent",
        explanation="minor slip",
        category="conceptual",
        severity="minor",
        confidence=0.1,
        domain="classical-ml",
    )
    chat = FakeChat(
        LLMReply(
            content=None,
            tool_calls=[
                ToolCallRequest(
                    id="call_1",
                    name="record_job_fit_analysis",
                    arguments={"matching_strengths": ["Gradient descent"], "gaps": ["Kubernetes"]},
                )
            ],
        )
    )

    result = analyze_job_fit("ML engineer role requiring gradient-based optimization and Kubernetes.", _chat_fn=chat)

    assert result == JobFitAnalysis(matching_strengths=["Gradient descent"], gaps=["Kubernetes"])
    assert chat.calls[0]["tool_choice"] == {"type": "function", "function": {"name": "record_job_fit_analysis"}}
    assert chat.calls[0]["tools"][0]["function"]["name"] == "record_job_fit_analysis"
