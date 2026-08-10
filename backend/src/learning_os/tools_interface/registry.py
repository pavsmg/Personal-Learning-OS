from dataclasses import dataclass
from typing import Any, Callable

TOOLS: dict[str, "Tool"] = {}


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]


def register(name: str, description: str, handler: Callable[..., Any]) -> None:
    TOOLS[name] = Tool(name=name, description=description, handler=handler)


def call_tool(name: str, **kwargs: Any) -> Any:
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    return TOOLS[name].handler(**kwargs)
