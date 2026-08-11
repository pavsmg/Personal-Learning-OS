import inspect
from typing import Any, Callable

from mcp.server import MCPServer

from learning_os.tools_interface import TOOLS, call_tool


def _public_wrapper(name: str, handler: Callable[..., Any]) -> Callable[..., Any]:
    """MCP's introspection rejects leading-underscore parameters outright
    (e.g. career/service.py's `_chat_fn`, an internal test-injection hook,
    not part of the public contract — tools_interface/registry.py already
    excludes these from our own JSON-schema generation the same way).
    Wraps the handler with a signature that strips them, so MCP sees the
    same public parameter set our own registry already computes, without
    needing per-tool special-casing."""

    original_signature = inspect.signature(handler, eval_str=True)
    public_parameters = [p for p in original_signature.parameters.values() if not p.name.startswith("_")]

    def wrapper(**kwargs: Any) -> Any:
        return call_tool(name, **kwargs)

    wrapper.__signature__ = original_signature.replace(parameters=public_parameters)  # type: ignore[attr-defined]
    wrapper.__name__ = name
    wrapper.__doc__ = handler.__doc__
    return wrapper


def build_server() -> MCPServer:
    server = MCPServer(name="learning-os", description="Personal Learning OS backend tools.")
    for name, tool in TOOLS.items():
        server.add_tool(_public_wrapper(name, tool.handler), name=name, description=tool.description)
    return server


def run() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    run()
