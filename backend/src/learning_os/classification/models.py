from pathlib import Path

from pydantic import BaseModel, ConfigDict


class DomainClassification(BaseModel):
    model_config = ConfigDict(frozen=True)

    note_title: str
    note_path: Path
    domain: str
    confidence: float
