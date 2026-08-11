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
