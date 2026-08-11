from typing import Any

from learning_os.tools_interface import TOOLS


def to_realtime_tools(tool_names: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": name,
            "description": TOOLS[name].description,
            "parameters": TOOLS[name].parameters_schema,
        }
        for name in tool_names
    ]
