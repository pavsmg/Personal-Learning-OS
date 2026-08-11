import json
from typing import Any


def serialize_for_json(value: Any) -> Any:
    if isinstance(value, list):
        return [serialize_for_json(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def to_json(value: Any) -> str:
    return json.dumps(value)
