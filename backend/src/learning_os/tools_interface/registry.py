import inspect
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import create_model

TOOLS: dict[str, "Tool"] = {}


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    parameters_schema: dict[str, Any]


def _schema_for(handler: Callable[..., Any]) -> dict[str, Any]:
    signature = inspect.signature(handler)
    fields = {
        name: (
            param.annotation if param.annotation is not inspect.Parameter.empty else Any,
            param.default if param.default is not inspect.Parameter.empty else ...,
        )
        for name, param in signature.parameters.items()
    }
    model = create_model(f"{handler.__name__}_Params", **fields)
    return model.model_json_schema()


def register(name: str, description: str, handler: Callable[..., Any]) -> None:
    TOOLS[name] = Tool(
        name=name,
        description=description,
        handler=handler,
        parameters_schema=_schema_for(handler),
    )


def call_tool(name: str, **kwargs: Any) -> Any:
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    return TOOLS[name].handler(**kwargs)
