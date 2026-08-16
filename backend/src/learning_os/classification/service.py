import math
from pathlib import Path
from typing import Callable

from learning_os.classification.models import DomainClassification
from learning_os.config import get_settings
from learning_os.llm_client import embed_texts
from learning_os.retrieval.loader import FRONTMATTER_RE, load_vault, parse_frontmatter
from learning_os.retrieval.models import Note
from learning_os.sessions.service import DEFAULT_DOMAIN, infer_domain

EmbedFn = Callable[[list[str]], list[list[float]]]

# Phase 2 of decisions.md #49: below this cosine similarity, a note is left
# unclassified rather than assigned its best-scoring domain anyway -- same
# honesty pattern as #45's estimate_mastery reporting absence instead of a
# forced score. Not tuned against real data yet, a defensible starting
# point in the same spirit as BM25_K1/OVERDUE_TIE_BUCKET_SIZE elsewhere.
DEFAULT_CONFIDENCE_THRESHOLD = 0.6
# text-embedding-3-small's real limit is 8191 tokens; this is a character
# count, not a token count, so it's a defensive truncation well under that
# limit, not a precise cutoff -- keeps one abnormally long note from
# dominating a batch call's cost.
MAX_CHARS_PER_NOTE = 8000
# infer_domain's tag fallback (note.tags[0]) picks up whatever tag happens
# to be first in a note's body, which is often the first *organizational*
# tag rather than a subject one -- found live against the real vault: a
# one-note tag like "define" or "ideas" produces a centroid from a single
# example, and a well-populated one can still be a meta-tag rather than a
# domain (see EXCLUDED_CLASS_DOMAINS). A class built from fewer than this
# many labeled notes is dropped rather than used -- not a fix for the
# meta-tag case, but it does remove every true one-off.
MIN_CLASS_SIZE = 5
# Real, well-populated vault tags confirmed (by inspection, not a
# heuristic) to mark a cross-cutting concept rather than a subject domain
# -- "transconcept" groups notes like Object/Callback/Event/Serialization,
# which have nothing in common as a *topic*. A count threshold alone can't
# catch this (25 real notes, well above MIN_CLASS_SIZE), so it's an
# explicit, user-confirmed exclusion instead of a guessed one.
EXCLUDED_CLASS_DOMAINS = frozenset({"transconcept"})


def _note_text(note: Note) -> str:
    return f"{note.title}\n\n{note.body[:MAX_CHARS_PER_NOTE]}"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _average_vector(vectors: list[list[float]]) -> list[float]:
    length = len(vectors[0])
    return [sum(vector[i] for vector in vectors) / len(vectors) for i in range(length)]


def _group_labeled_notes(notes: dict[str, Note]) -> dict[str, list[Note]]:
    """Notes infer_domain already resolves to a real domain -- frontmatter,
    language-title match, tag, or (#49) folder -- grouped by that domain.
    Excludes DEFAULT_DOMAIN ("general"): it isn't a domain anyone chose, so
    it's not a class to classify anything into (decisions.md #49/#50). Also
    excludes EXCLUDED_CLASS_DOMAINS and any group smaller than
    MIN_CLASS_SIZE -- both found necessary against the real vault, not
    speculative (decisions.md #51)."""
    groups: dict[str, list[Note]] = {}
    for note in notes.values():
        domain = infer_domain(note)
        if domain == DEFAULT_DOMAIN or domain in EXCLUDED_CLASS_DOMAINS:
            continue
        groups.setdefault(domain, []).append(note)
    return {domain: domain_notes for domain, domain_notes in groups.items() if len(domain_notes) >= MIN_CLASS_SIZE}


def build_class_centroids(notes: dict[str, Note], _embed_fn: EmbedFn = embed_texts) -> dict[str, list[float]]:
    """One centroid per domain already in real use elsewhere in the vault:
    the average embedding of every note that domain already resolves to via
    infer_domain. Deliberately not persisted -- decisions.md #2's
    provider-resilience principle means embedding-engine output shouldn't
    become durable data; recomputing from source notes on every run keeps
    a provider swap free of migration concerns."""
    labeled = _group_labeled_notes(notes)
    centroids = {}
    for domain, domain_notes in labeled.items():
        vectors = _embed_fn([_note_text(note) for note in domain_notes])
        centroids[domain] = _average_vector(vectors)
    return centroids


def classify_unlabeled_notes(
    vault_path: Path | None = None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    _embed_fn: EmbedFn = embed_texts,
) -> list[DomainClassification]:
    """Classify every vault note infer_domain would otherwise leave at
    "general" against the domains already in real use elsewhere in the
    vault, by embedding similarity to build_class_centroids' output. Below
    `threshold`, a note is left out of the result entirely rather than
    assigned its best (but weak) match -- no label forced without real
    confidence behind it. Read-only: doesn't write anything.
    `apply_classifications` does that, separately, so a caller can always
    inspect the result before touching a single file."""
    vault_path = vault_path or get_settings().vault_path
    notes = load_vault(vault_path)

    centroids = build_class_centroids(notes, _embed_fn=_embed_fn)
    if not centroids:
        return []

    unlabeled = [note for note in notes.values() if infer_domain(note) == DEFAULT_DOMAIN]
    if not unlabeled:
        return []

    vectors = _embed_fn([_note_text(note) for note in unlabeled])

    results = []
    for note, vector in zip(unlabeled, vectors):
        best_domain, best_score = max(
            ((domain, _cosine_similarity(vector, centroid)) for domain, centroid in centroids.items()),
            key=lambda item: item[1],
        )
        if best_score >= threshold:
            results.append(
                DomainClassification(note_title=note.title, note_path=note.path, domain=best_domain, confidence=best_score)
            )
    return results


def _insert_domain_frontmatter(text: str, domain: str) -> str:
    """Text-level insertion, not a YAML round-trip: preserves the note's
    existing frontmatter formatting/comments/key ordering byte-for-byte
    except for the one new line, rather than risking yaml.dump reshuffling
    content the user wrote by hand."""
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return f"---\ndomain: {domain}\n---\n\n{text}"
    frontmatter_block = text[: match.end()]
    closing_delimiter = "---\n"
    new_frontmatter_block = frontmatter_block[: -len(closing_delimiter)] + f"domain: {domain}\n" + closing_delimiter
    return new_frontmatter_block + text[match.end() :]


def apply_classifications(classifications: list[DomainClassification]) -> int:
    """Writes domain: <label> into each note's real frontmatter block on
    disk -- the one place in this project that mutates the vault instead
    of only reading it (decisions.md #51, a deliberate choice the user
    made explicitly). Skips (doesn't overwrite) a note that already gained
    a domain key since classify_unlabeled_notes ran, rather than
    clobbering it. Returns how many files were actually written."""
    written = 0
    for classification in classifications:
        text = classification.note_path.read_text(encoding="utf-8")
        frontmatter, _ = parse_frontmatter(text)
        if frontmatter.get("domain"):
            continue
        classification.note_path.write_text(_insert_domain_frontmatter(text, classification.domain), encoding="utf-8")
        written += 1
    return written
