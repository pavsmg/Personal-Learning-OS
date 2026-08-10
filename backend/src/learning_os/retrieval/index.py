import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from learning_os.retrieval.loader import load_vault
from learning_os.retrieval.models import Note, NoteSummary

TOKEN_RE = re.compile(r"[a-z0-9]+")
TITLE_WEIGHT, TAG_WEIGHT, BODY_WEIGHT = 5, 3, 1
EXACT_TITLE_BONUS = 50
SNIPPET_LENGTH = 160


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class _SearchEntry:
    __slots__ = ("note", "title_tokens", "body_tokens", "tag_set")

    def __init__(self, note: Note) -> None:
        self.note = note
        self.title_tokens = Counter(_tokenize(note.title))
        self.body_tokens = Counter(_tokenize(note.body))
        self.tag_set = {tag.lower() for tag in note.tags}


class VaultIndex:
    def __init__(self, notes: dict[str, Note]) -> None:
        self._notes = notes
        self._entries = {key: _SearchEntry(note) for key, note in notes.items()}
        self._backlinks = self._build_backlinks()

    def _build_backlinks(self) -> dict[str, set[str]]:
        backlinks: dict[str, set[str]] = defaultdict(set)
        for note in self._notes.values():
            source_key = note.title.lower()
            for target in note.outgoing_links:
                target_key = target.lower()
                if target_key in self._notes:
                    backlinks[target_key].add(source_key)
        return backlinks

    def get(self, title: str) -> Note | None:
        return self._notes.get(title.strip().lower())

    def search(self, query: str, limit: int = 10) -> list[NoteSummary]:
        query_lower = query.strip().lower()
        query_tokens = _tokenize(query_lower)
        if not query_tokens:
            return []

        scored = []
        for entry in self._entries.values():
            score = 0
            if query_lower in entry.note.title.lower():
                score += EXACT_TITLE_BONUS
            for token in query_tokens:
                score += entry.title_tokens.get(token, 0) * TITLE_WEIGHT
                score += entry.body_tokens.get(token, 0) * BODY_WEIGHT
                if token in entry.tag_set:
                    score += TAG_WEIGHT
            if score > 0:
                scored.append((score, entry.note.title.lower(), entry.note))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [self._to_summary(note) for _, _, note in scored[:limit]]

    def related(self, title: str) -> list[NoteSummary]:
        note = self.get(title)
        if note is None:
            return []

        key = note.title.lower()
        outgoing = {t.lower() for t in note.outgoing_links if t.lower() in self._notes}
        incoming = self._backlinks.get(key, set())
        related_keys = sorted((outgoing | incoming) - {key})
        return [self._to_summary(self._notes[k]) for k in related_keys]

    @staticmethod
    def _to_summary(note: Note) -> NoteSummary:
        snippet = note.body.strip().replace("\n", " ")[:SNIPPET_LENGTH]
        return NoteSummary(title=note.title, snippet=snippet, tags=note.tags)


@lru_cache
def get_vault_index(vault_path: Path) -> VaultIndex:
    return VaultIndex(load_vault(vault_path))
