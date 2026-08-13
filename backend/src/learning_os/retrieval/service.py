from learning_os.config import get_settings
from learning_os.retrieval.index import get_vault_index
from learning_os.retrieval.models import Note, NoteSummary


def search_notes(query: str, limit: int = 10) -> list[NoteSummary]:
    return get_vault_index(get_settings().vault_path).search(query, limit=limit)


def get_note(title: str) -> Note | None:
    return get_vault_index(get_settings().vault_path).get(title)


def related_notes(title: str) -> list[NoteSummary]:
    return get_vault_index(get_settings().vault_path).related(title)


def concept_importance(title: str) -> int:
    return get_vault_index(get_settings().vault_path).importance(title)


def most_important_notes(limit: int = 20) -> list[NoteSummary]:
    return get_vault_index(get_settings().vault_path).most_important(limit=limit)
