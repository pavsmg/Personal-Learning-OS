from pydantic import BaseModel, ConfigDict

from learning_os.mistakes.models import EvidenceOutcome


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


# decisions.md #44: the end-of-session grading pass's structured output.
# rationale is required, not optional -- it forces a justification for
# every grade and is what makes a correct_with_application grade checkable
# against pedagogy.md's demand (a real rule-11 transfer exchange, not a
# fluent-sounding transcript). Not persisted onto Evidence itself (no
# rationale column there); written to the SessionLog instead so it's
# sampleable after the fact.
class ConceptGrade(BaseModel):
    concept: str
    outcome: EvidenceOutcome
    quality: float
    rationale: str


class GradingResult(BaseModel):
    grades: list[ConceptGrade]
