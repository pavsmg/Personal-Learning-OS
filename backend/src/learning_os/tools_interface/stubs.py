from typing import Any

# Language module and Stats don't have a dedicated module folder yet —
# these stubs live here provisionally until their own milestone gives them
# one. Progression (get_learning_profile/estimate_mastery/recommend_review)
# used to live here too but moved into mistakes/service.py at Milestone 6;
# Career (summarize_skills_for_cv/analyze_job_fit) moved into career/service.py
# at Milestone 7 — both entirely computed from real data now.


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
