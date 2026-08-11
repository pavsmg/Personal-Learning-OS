from learning_os.conversation.prompt import TUTORING_TOOLS
from learning_os.realtime.tools import to_realtime_tools


def test_to_realtime_tools_uses_flat_shape_not_chat_completions_envelope():
    tools = to_realtime_tools(["search_notes"])

    assert len(tools) == 1
    tool = tools[0]
    assert tool["type"] == "function"
    assert tool["name"] == "search_notes"
    assert "description" in tool
    assert "parameters" in tool
    assert "function" not in tool  # not the nested Chat Completions envelope


def test_to_realtime_tools_preserves_real_parameters_schema():
    tools = to_realtime_tools(["get_note"])

    assert tools[0]["parameters"]["required"] == ["title"]


def test_tutoring_tools_includes_mistake_memory_and_language_tools():
    tools = to_realtime_tools(TUTORING_TOOLS)

    names = {t["name"] for t in tools}
    assert names == {
        "search_notes",
        "get_note",
        "related_notes",
        "save_mistake",
        "get_recent_mistakes",
        "get_language_profile",
        "get_curriculum",
    }
