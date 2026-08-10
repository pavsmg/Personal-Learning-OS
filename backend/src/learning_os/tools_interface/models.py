from pydantic import BaseModel, ConfigDict


class MasteryEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: str
    concept: str
    mastery: float


class JobFitAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    matching_strengths: list[str]
    gaps: list[str]
