from typing import Any

from learning_os.language.loader import language_dir, parse_practice_log, parse_roadmap
from learning_os.mistakes import get_learning_profile


def get_language_profile(language: str) -> dict[str, Any]:
    directory = language_dir(language)
    if not directory.exists():
        raise ValueError(f"No Language-Lab data for language: {language!r}")

    domain = language.lower()
    practice_log_path = directory / "PRACTICE_LOG.md"
    recent_practice = (
        [entry.model_dump() for entry in parse_practice_log(practice_log_path.read_text(encoding="utf-8"))]
        if practice_log_path.exists()
        else []
    )

    return {
        "language": domain,
        "mastery": [estimate.model_dump() for estimate in get_learning_profile(domain=domain)],
        "recent_practice": recent_practice,
        "roadmap_status": get_curriculum(language),
    }


def get_curriculum(language: str) -> list[str]:
    directory = language_dir(language)
    if not directory.exists():
        raise ValueError(f"No Language-Lab data for language: {language!r}")

    roadmap_path = directory / "ROADMAP.md"
    if not roadmap_path.exists():
        return []
    return parse_roadmap(roadmap_path.read_text(encoding="utf-8"))


def retrieve_vocabulary(language: str, topic: str | None = None) -> list[str]:
    """Stub — Language-Lab doesn't track vocabulary yet (its own backlog item,
    not built)."""
    raise NotImplementedError("retrieve_vocabulary is not implemented yet — Language-Lab has no vocabulary tracking")
