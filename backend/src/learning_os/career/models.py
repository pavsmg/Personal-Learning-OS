from pydantic import BaseModel, ConfigDict


class JobFitAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    matching_strengths: list[str]
    gaps: list[str]
