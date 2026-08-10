from typing import Any

from learning_os.tools_interface.models import JobFitAnalysis, MasteryEstimate

# Progression, Language module, Stats, and Career don't have a dedicated
# module folder yet (unlike retrieval/mistakes/sessions) — these stubs live
# here provisionally until their own milestone gives them one.


def get_learning_profile(domain: str) -> list[MasteryEstimate]:
    """Stub — implemented in Milestone 6."""
    raise NotImplementedError("get_learning_profile is not implemented yet (Milestone 6)")


def estimate_mastery(domain: str, concept: str) -> float:
    """Stub — implemented in Milestone 6."""
    raise NotImplementedError("estimate_mastery is not implemented yet (Milestone 6)")


def recommend_review(domain: str | None = None) -> list[str]:
    """Stub — implemented in Milestone 6."""
    raise NotImplementedError("recommend_review is not implemented yet (Milestone 6)")


def get_language_profile(language: str) -> dict[str, Any]:
    """Stub — implemented in Milestone 9."""
    raise NotImplementedError("get_language_profile is not implemented yet (Milestone 9)")


def get_curriculum(language: str) -> list[str]:
    """Stub — implemented in Milestone 9."""
    raise NotImplementedError("get_curriculum is not implemented yet (Milestone 9)")


def retrieve_vocabulary(language: str, topic: str | None = None) -> list[str]:
    """Stub — implemented in Milestone 9."""
    raise NotImplementedError("retrieve_vocabulary is not implemented yet (Milestone 9)")


def get_learning_statistics() -> dict[str, Any]:
    """Stub — not yet scheduled to a milestone."""
    raise NotImplementedError("get_learning_statistics is not implemented yet")


def summarize_skills_for_cv() -> str:
    """Stub — implemented in Milestone 7."""
    raise NotImplementedError("summarize_skills_for_cv is not implemented yet (Milestone 7)")


def analyze_job_fit(job_description: str) -> JobFitAnalysis:
    """Stub — implemented in Milestone 7."""
    raise NotImplementedError("analyze_job_fit is not implemented yet (Milestone 7)")
