import json
from typing import Any

_DIVIDER = "-" * 60


def print_tool_call(number: int, name: str, arguments: dict[str, Any], result_json: str) -> None:
    """Full, pretty-printed rendering of one tool call for --debug: complete
    arguments and complete result, not a single line truncated at 200 chars."""
    try:
        result_display = json.dumps(json.loads(result_json), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        result_display = result_json
    args_display = json.dumps(arguments, indent=2, ensure_ascii=False, default=str)
    print(f"\n{_DIVIDER}")
    print(f"[tool call #{number}] {name}")
    print(_DIVIDER)
    print("arguments:")
    print(args_display)
    print("result:")
    print(result_display)
    print(_DIVIDER)
