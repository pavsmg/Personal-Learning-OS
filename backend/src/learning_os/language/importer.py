from learning_os.language.loader import language_dir, parse_mistakes
from learning_os.language.models import MistakePattern
from learning_os.language.service import LANGUAGES
from learning_os.mistakes import get_learning_profile, save_mistake

STATUS_CONFIDENCE = {"Active": 0.7, "Watching": 0.4, "Resolved": 0.1}
DEFAULT_CONFIDENCE = 0.4


def _severity_for(pattern: MistakePattern) -> str:
    return "moderate" if pattern.seen_count >= 2 else "minor"


def import_language_mistakes(language: str) -> int:
    mistakes_path = language_dir(language) / "MISTAKES.md"
    if not mistakes_path.exists():
        return 0

    domain = language.lower()
    already_imported = {m.concept.lower() for m in get_learning_profile(domain=domain)}

    count = 0
    for pattern in parse_mistakes(mistakes_path.read_text(encoding="utf-8")):
        if pattern.pattern.lower() in already_imported:
            continue
        save_mistake(
            concept=pattern.pattern,
            explanation=pattern.description,
            category=pattern.category,
            severity=_severity_for(pattern),
            confidence=STATUS_CONFIDENCE.get(pattern.status, DEFAULT_CONFIDENCE),
            domain=domain,
            related_notes=[],
        )
        count += 1
    return count


def import_all_languages() -> dict[str, int]:
    return {language: import_language_mistakes(language) for language in LANGUAGES}
