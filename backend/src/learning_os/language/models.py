from pydantic import BaseModel, ConfigDict


class MistakePattern(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    pattern: str
    seen_count: int
    status: str
    description: str


class PracticeLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: str
    focus: str
    raw: str
