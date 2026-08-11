import asyncio

from mcp.client._memory import InMemoryTransport
from mcp.client.session import ClientSession

from learning_os.mcp_server import build_server
from learning_os.tools_interface import TOOLS


def test_build_server_registers_every_tool():
    server = build_server()

    registered = server._tool_manager.list_tools()

    assert {tool.name for tool in registered} == set(TOOLS.keys())
    for tool in registered:
        assert tool.description == TOOLS[tool.name].description


async def _list_and_call(server, tool_name, arguments):
    transport = InMemoryTransport(server)
    async with transport as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            result = await session.call_tool(tool_name, arguments)
            return listed, result


def test_real_protocol_call_through_dispatches_to_search_notes(tmp_path, monkeypatch):
    (tmp_path / "Gradient descent.md").write_text("core optimization concept\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    server = build_server()
    listed, result = asyncio.run(_list_and_call(server, "search_notes", {"query": "gradient descent"}))

    assert len(listed.tools) == len(TOOLS)
    assert result.is_error is not True
    assert "Gradient descent" in result.content[0].text


def test_real_protocol_call_through_surfaces_stub_as_error():
    server = build_server()

    _, result = asyncio.run(_list_and_call(server, "get_learning_statistics", {}))

    assert result.is_error is True
    assert "not implemented yet" in result.content[0].text
