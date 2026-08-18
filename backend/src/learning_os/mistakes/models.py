from datetime import datetime
from typing import Literal

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


# decisions.md #44: the two-sided counterpart to MistakeEntry. Written by
# sessions/grading.py's end-of-session pass, never per-turn -- see that
# module for why. "not_reached" is a real, written outcome (a planned
# concept the session never actually quizzed), not an omission; it is
# excluded from scoring everywhere it's read (mistakes/service.py), so
# discussion without a recall check still can't masquerade as evidence.
EvidenceOutcome = Literal["not_reached", "incorrect", "partial", "correct", "correct_with_application"]


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: str
    concept: str
    timestamp: datetime
    outcome: EvidenceOutcome
    quality: float
    source: str
    session_id: str


class MasteryEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: str
    concept: str
    conceptual_understanding: float
    # mistake_count keeps its original, narrower meaning: mistakes-table
    # rows only. observation_count is the new two-sided total (mistakes +
    # scoring-eligible evidence) -- additive, so nothing reading
    # mistake_count today silently changes meaning underneath it.
    mistake_count: int
    observation_count: int
