from collections import Counter
from pathlib import Path

from learning_os.classification.models import DomainClassification
from learning_os.classification.service import EXCLUDED_CLASS_DOMAINS
from learning_os.config import get_settings
from learning_os.retrieval.index import VaultIndex
from learning_os.retrieval.loader import load_vault
from learning_os.sessions.service import DEFAULT_DOMAIN, infer_domain

# Checked against the real vault before picking a number: with >=2 votes a
# note only needs two labeled neighbors to agree, and that let through real
# mislabels (e.g. "Windows" -> linux 2/2, "MS-DOS" -> linux 2/2 -- both
# linked *in contrast to* Linux notes, not because they belong to that
# domain). Raising the bar to >=3 removed every case like that on manual
# review of the real result set (123 -> 64 notes) without losing anything
# that looked wrong.
DEFAULT_MIN_VOTES = 3


def classify_by_neighbor_vote(vault_path: Path | None = None, min_votes: int = DEFAULT_MIN_VOTES) -> list[DomainClassification]:
    """For every note infer_domain leaves at DEFAULT_DOMAIN, look at its
    real graph neighbors (VaultIndex.related's mutual/outgoing/incoming-
    link tiers, combined) and inherit whichever real domain has a clear
    plurality among them. A neighbor with no real domain, or one in
    EXCLUDED_CLASS_DOMAINS (a meta-tag like "transconcept", same as #51's
    embeddings classifier), doesn't count as a vote. Below `min_votes` or
    tied at the top, a note is left unclassified -- same honesty pattern
    as classify_unlabeled_notes' confidence threshold, just measured in
    votes instead of cosine similarity. Read-only: doesn't write anything,
    same contract as classify_unlabeled_notes -- apply_classifications
    does the writing, for either method's output alike."""
    vault_path = vault_path or get_settings().vault_path
    notes = load_vault(vault_path)
    index = VaultIndex(notes)

    unlabeled = [note for note in notes.values() if infer_domain(note) == DEFAULT_DOMAIN]

    results = []
    for note in unlabeled:
        neighbor_domains = []
        for neighbor_summary in index.related(note.title):
            neighbor = notes.get(neighbor_summary.title.lower())
            if neighbor is None:
                continue
            domain = infer_domain(neighbor)
            if domain == DEFAULT_DOMAIN or domain in EXCLUDED_CLASS_DOMAINS:
                continue
            neighbor_domains.append(domain)

        if not neighbor_domains:
            continue

        counts = Counter(neighbor_domains)
        top_domain, top_votes = counts.most_common(1)[0]
        if top_votes < min_votes:
            continue
        tied = [domain for domain, votes in counts.items() if votes == top_votes]
        if len(tied) > 1:
            continue

        results.append(
            DomainClassification(
                note_title=note.title,
                note_path=note.path,
                domain=top_domain,
                confidence=top_votes / len(neighbor_domains),
            )
        )
    return results
