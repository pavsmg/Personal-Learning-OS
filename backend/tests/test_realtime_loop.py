import asyncio
import json

from learning_os.realtime.loop import handle_tool_call


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")


def test_handle_tool_call_dispatches_to_real_search_notes(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Gradient descent.md": "core optimization concept.\n"})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    output = asyncio.run(handle_tool_call("search_notes", {"query": "gradient descent"}))

    results = json.loads(output)
    assert results[0]["title"] == "Gradient descent"


def test_handle_tool_call_unknown_tool_returns_error_json_not_raise():
    output = asyncio.run(handle_tool_call("does_not_exist", {}))

    result = json.loads(output)
    assert "does_not_exist" in result["error"]


def test_handle_tool_call_handler_exception_returns_error_json_not_raise(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    output = asyncio.run(handle_tool_call("get_note", {}))  # missing required 'title' arg

    result = json.loads(output)
    assert "error" in result
