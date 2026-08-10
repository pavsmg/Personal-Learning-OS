from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MistakeEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    concept: str
    explanation: str
    category: str
    severity: str
    timestamp: datetime
    corrected: bool
    confidence: float
    related_notes: list[str]
