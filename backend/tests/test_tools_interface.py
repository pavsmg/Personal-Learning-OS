import pytest

from learning_os.tools_interface import TOOLS, call_tool

EXPECTED_TOOL_NAMES = {
    "search_notes",
    "get_note",
    "related_notes",
    "get_learning_profile",
    "estimate_mastery",
    "recommend_review",
    "search_mistakes",
    "save_mistake",
    "get_recent_mistakes",
    "create_session",
    "finish_session",
    "summarize_session",
    "get_language_profile",
    "get_curriculum",
    "retrieve_vocabulary",
    "get_learning_statistics",
    "summarize_skills_for_cv",
    "analyze_job_fit",
}


def test_registry_contains_every_tools_md_function():
    assert set(TOOLS.keys()) == EXPECTED_TOOL_NAMES


def test_call_tool_dispatches_to_real_retrieval_implementation(tmp_path, monkeypatch):
    (tmp_path / "Gradient descent.md").write_text("core optimization concept\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    results = call_tool("search_notes", query="gradient descent")

    assert [r.title for r in results] == ["Gradient descent"]


def test_call_tool_stub_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        call_tool("get_learning_statistics")


def test_call_tool_unknown_name_raises_key_error():
    with pytest.raises(KeyError):
        call_tool("does_not_exist")


def test_search_notes_schema_has_required_and_optional_params():
    schema = TOOLS["search_notes"].parameters_schema

    assert schema["required"] == ["query"]
    assert schema["properties"]["query"]["type"] == "string"
    assert schema["properties"]["limit"]["type"] == "integer"
    assert schema["properties"]["limit"]["default"] == 10


def test_get_learning_statistics_schema_has_no_properties():
    schema = TOOLS["get_learning_statistics"].parameters_schema

    assert schema["properties"] == {}


def test_recommend_review_schema_optional_domain_not_required():
    schema = TOOLS["recommend_review"].parameters_schema

    assert "required" not in schema or "domain" not in schema["required"]


def test_save_mistake_schema_requires_domain():
    schema = TOOLS["save_mistake"].parameters_schema

    assert "domain" in schema["required"]
    assert schema["properties"]["domain"]["type"] == "string"
