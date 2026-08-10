from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class Note(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    path: Path
    frontmatter: dict[str, Any]
    tags: list[str]
    body: str
    outgoing_links: list[str]


class NoteSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    snippet: str
    tags: list[str]
