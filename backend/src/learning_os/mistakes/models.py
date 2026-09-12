from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MistakeEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    timestamp: datetime
    corrected: bool
    # decisions.md #63: confidence is the observer's certainty (0-1), not
    # the size of the knowledge gap -- enforced here, not just documented.
    confidence: float = Field(ge=0.0, le=1.0)
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

    domain: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    timestamp: datetime
    outcome: EvidenceOutcome
    # decisions.md #63: quality is the grader's certainty in this grade
    # (0-1), enforced here so an out-of-range value fails fast at the
    # write path instead of silently skewing scheduling math.
    quality: float = Field(ge=0.0, le=1.0)
    source: str = Field(min_length=1)
    session_id: str = Field(min_length=1)


class EvidenceReview(BaseModel):
    """decisions.md #63: an immutable human correction of one evidence
    row's outcome. The original row is never edited or deleted -- reviews
    form their own append-only history and the latest one wins for
    scoring. Result-only by design: concept/domain attribution stays as
    the grader wrote it."""

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    previous_outcome: EvidenceOutcome
    new_outcome: EvidenceOutcome
    reason: str = Field(min_length=1)
    reviewer: str = Field(min_length=1, default="human")
    timestamp: datetime


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
