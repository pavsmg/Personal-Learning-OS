from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MistakeEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: str
    concept: str
    explanation: str
    category: str
    severity: str
    timestamp: datetime
    corrected: bool
    confidence: float
    related_notes: list[str]


class MasteryEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: str
    concept: str
    conceptual_understanding: float
    mistake_count: int
