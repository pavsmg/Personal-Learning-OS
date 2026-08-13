import math
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
# Standard Okapi BM25 defaults (Robertson/Sparck Jones) -- textbook values,
# not vault-tuned, deliberately: adopting a real, well-understood ranking
# formula instead of more hand-picked magic numbers is the point.
BM25_K1 = 1.5
BM25_B = 0.75


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class _SearchEntry:
    __slots__ = ("note", "title_tokens", "body_tokens", "tag_set", "title_len", "body_len")

    def __init__(self, note: Note) -> None:
        self.note = note
        self.title_tokens = Counter(_tokenize(note.title))
        self.body_tokens = Counter(_tokenize(note.body))
        self.tag_set = {tag.lower() for tag in note.tags}
        self.title_len = sum(self.title_tokens.values())
        self.body_len = sum(self.body_tokens.values())


class VaultIndex:
    def __init__(self, notes: dict[str, Note]) -> None:
        self._notes = notes
        self._entries = {key: _SearchEntry(note) for key, note in notes.items()}
        self._backlinks = self._build_backlinks()
        self._n = len(self._entries)
        self._avg_title_len = self._average_length("title_len")
        self._avg_body_len = self._average_length("body_len")
        self._title_df = self._document_frequencies("title_tokens")
        self._body_df = self._document_frequencies("body_tokens")

    def _build_backlinks(self) -> dict[str, set[str]]:
        backlinks: dict[str, set[str]] = defaultdict(set)
        for note in self._notes.values():
            source_key = note.title.lower()
            for target in note.outgoing_links:
                target_key = target.lower()
                if target_key in self._notes:
                    backlinks[target_key].add(source_key)
        return backlinks

    def _importance(self, key: str) -> int:
        """Backlink count for a note key -- how many other notes point at
        it. The same in-degree centrality signal `most_important` ranks
        the whole vault by; shared here so `related()`'s tier tiebreak and
        `most_important`'s own ranking can't silently drift apart."""
        return len(self._backlinks.get(key, set()))

    def _average_length(self, length_attr: str) -> float:
        if not self._entries:
            return 0.0
        return sum(getattr(entry, length_attr) for entry in self._entries.values()) / len(self._entries)

    def _document_frequencies(self, tokens_attr: str) -> dict[str, int]:
        df: dict[str, int] = defaultdict(int)
        for entry in self._entries.values():
            for term in getattr(entry, tokens_attr):
                df[term] += 1
        return df

    def get(self, title: str) -> Note | None:
        return self._notes.get(title.strip().lower())

    def importance(self, title: str) -> int:
        """Public single-note counterpart to most_important's ranking.
        Returns 0 if the title doesn't resolve to a real vault note
        (handled, not an error): callers outside retrieval routinely deal
        with tracked "concept" strings that were never vault note titles
        at all -- 6 of 10 in the real data today, all freeform
        language-mistake descriptions."""
        key = title.strip().lower()
        if key not in self._notes:
            return 0
        return self._importance(key)

    def _bm25_idf(self, term: str, df: dict[str, int]) -> float:
        # +1 inside the log keeps this non-negative even for terms that
        # appear in most of the vault, unlike the classic Robertson-Sparck
        # Jones IDF (which can go negative and start *penalizing* common
        # terms) -- appropriate here since an over-common word should be
        # weighted down toward zero, not flipped into a negative signal.
        return math.log(1 + (self._n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))

    def _bm25_field_score(
        self, query_tokens: list[str], entry: "_SearchEntry", tokens_attr: str, length: int, avg_length: float, df: dict[str, int]
    ) -> float:
        if avg_length == 0:
            return 0.0
        field_tokens: Counter = getattr(entry, tokens_attr)
        score = 0.0
        for term in query_tokens:
            tf = field_tokens.get(term, 0)
            if tf == 0:
                continue
            idf = self._bm25_idf(term, df)
            denominator = tf + BM25_K1 * (1 - BM25_B + BM25_B * length / avg_length)
            score += idf * (tf * (BM25_K1 + 1)) / denominator
        return score

    def search(self, query: str, limit: int = 10) -> list[NoteSummary]:
        """BM25 per field (title, body), combined with the same relative
        field-importance weights the old naive scorer used
        (TITLE_WEIGHT/BODY_WEIGHT/TAG_WEIGHT), replacing raw un-normalized
        token counts. Fixes two real problems the old scorer had: no
        document-length normalization (a long note repeating a term many
        times used to systematically outrank a short, precise match — real
        example: "TCP-IP" outranking "TCP" itself for query "tcp"), and no
        IDF (a vault-wide-common word counted the same as a rare, specific
        one). EXACT_TITLE_BONUS is now true equality, not a substring
        check — the substring version gave "TCP-IP" the same bonus as
        "TCP" for query "tcp"."""
        query_lower = query.strip().lower()
        query_tokens = _tokenize(query_lower)
        if not query_tokens:
            return []

        scored = []
        for entry in self._entries.values():
            title_score = self._bm25_field_score(
                query_tokens, entry, "title_tokens", entry.title_len, self._avg_title_len, self._title_df
            )
            body_score = self._bm25_field_score(
                query_tokens, entry, "body_tokens", entry.body_len, self._avg_body_len, self._body_df
            )
            tag_score = sum(TAG_WEIGHT for token in query_tokens if token in entry.tag_set)
            exact_bonus = EXACT_TITLE_BONUS if entry.note.title.strip().lower() == query_lower else 0

            score = TITLE_WEIGHT * title_score + BODY_WEIGHT * body_score + tag_score + exact_bonus
            if score > 0:
                scored.append((score, entry.note.title.lower(), entry.note))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [self._to_summary(note) for _, _, note in scored[:limit]]

    def related(self, title: str) -> list[NoteSummary]:
        """Ranked, not just returned: notes this note *and* its author both
        linked to each other (mutual) come first — the strongest signal of
        real conceptual coupling, no new tracking needed, it's already in
        the graph. Then notes this note deliberately links out to (the
        author's own curated association). Backlink-only notes come last —
        something else happens to mention this note, which for a
        well-connected hub note can mean a broad index-style note that
        links to dozens of unrelated things alongside this one, not a sign
        this note is actually relevant to *it*. Within each tier, ranked by
        backlink count descending (the same in-degree signal
        `most_important` uses) — alphabetical is now only the tiebreak when
        importance is equal, not the primary order. Previously a single
        flat alphabetical list with no notion of which neighbor mattered
        more."""
        note = self.get(title)
        if note is None:
            return []

        key = note.title.lower()
        outgoing = {t.lower() for t in note.outgoing_links if t.lower() in self._notes} - {key}
        incoming = self._backlinks.get(key, set()) - {key}

        mutual = sorted(outgoing & incoming, key=lambda k: (-self._importance(k), k))
        outgoing_only = sorted(outgoing - incoming, key=lambda k: (-self._importance(k), k))
        incoming_only = sorted(incoming - outgoing, key=lambda k: (-self._importance(k), k))

        related_keys = mutual + outgoing_only + incoming_only
        return [self._to_summary(self._notes[k]) for k in related_keys]

    def most_important(self, limit: int = 20) -> list[NoteSummary]:
        """Vault notes ranked by in-degree (backlink count) -- how many
        other real notes point at this one -- highest first. Naive
        centrality: the more a concept is pointed at, the more it's
        treated as foundational to the vault. Deliberately just backlink
        count, not a note's own outgoing links: the claim is about being
        pointed at, not about how much a note references elsewhere. A
        cheap aggregation over `_backlinks`, already built at index time —
        no new indexing pass needed."""
        ranked = sorted(
            self._entries.keys(),
            key=lambda key: (-self._importance(key), key),
        )
        return [self._to_summary(self._notes[key]) for key in ranked[:limit]]

    @staticmethod
    def _to_summary(note: Note) -> NoteSummary:
        snippet = note.body.strip().replace("\n", " ")[:SNIPPET_LENGTH]
        return NoteSummary(title=note.title, snippet=snippet, tags=note.tags)


@lru_cache
def get_vault_index(vault_path: Path) -> VaultIndex:
    return VaultIndex(load_vault(vault_path))
