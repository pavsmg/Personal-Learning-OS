from pydantic import BaseModel, ConfigDict


class SessionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    domain: str
    objective: str
    concepts: list[str]
    target_difficulty: str
    expected_duration_minutes: int


class SessionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    summary: str
    concepts_reinforced: list[str]
