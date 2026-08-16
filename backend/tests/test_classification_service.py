from learning_os.classification.models import DomainClassification
from learning_os.classification.service import (
    MIN_CLASS_SIZE,
    apply_classifications,
    build_class_centroids,
    classify_unlabeled_notes,
)
from learning_os.config import get_settings
from learning_os.retrieval.loader import load_vault


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def labeled_notes(domain: str, count: int) -> dict[str, str]:
    """MIN_CLASS_SIZE-worth (or as requested) of distinctly-titled, real-shaped
    notes all frontmatter-tagged with the same domain -- most tests need a
    class that actually survives the size filter, not a single example."""
    return {f"{domain} note {i}.md": f"---\ndomain: {domain}\n---\nreal {domain} content, note {i}." for i in range(count)}


class FakeEmbedder:
    """Maps each note's title (the first line of the text service.py builds
    via _note_text) to a fixed vector, so tests can construct exact,
    intuitive cosine-similarity scenarios without a real embedding call.
    Falls back to a default vector for any title not given explicitly, so
    tests can label a whole class with one shared vector."""

    def __init__(self, vectors_by_title: dict[str, list[float]], default: list[float] | None = None):
        self._vectors_by_title = vectors_by_title
        self._default = default
        self.calls: list[list[str]] = []

    def __call__(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        results = []
        for text in texts:
            title = text.split("\n\n", 1)[0]
            if title in self._vectors_by_title:
                results.append(self._vectors_by_title[title])
            elif self._default is not None:
                results.append(self._default)
            else:
                raise KeyError(title)
        return results


def test_build_class_centroids_excludes_general_domain(tmp_path, monkeypatch):
    write_vault(tmp_path, {**labeled_notes("chemistry", MIN_CLASS_SIZE), "Untagged.md": "no frontmatter, no tag."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    notes = load_vault(get_settings().vault_path)
    embedder = FakeEmbedder({}, default=[1.0, 0.0])

    centroids = build_class_centroids(notes, _embed_fn=embedder)

    assert set(centroids) == {"chemistry"}


def test_build_class_centroids_drops_classes_below_min_size(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            **labeled_notes("chemistry", MIN_CLASS_SIZE),
            **labeled_notes("one-off-tag", MIN_CLASS_SIZE - 1),
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    notes = load_vault(get_settings().vault_path)
    embedder = FakeEmbedder({}, default=[1.0, 0.0])

    centroids = build_class_centroids(notes, _embed_fn=embedder)

    assert set(centroids) == {"chemistry"}


def test_build_class_centroids_excludes_transconcept_regardless_of_size(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            **labeled_notes("chemistry", MIN_CLASS_SIZE),
            **labeled_notes("transconcept", MIN_CLASS_SIZE + 20),
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    notes = load_vault(get_settings().vault_path)
    embedder = FakeEmbedder({}, default=[1.0, 0.0])

    centroids = build_class_centroids(notes, _embed_fn=embedder)

    assert set(centroids) == {"chemistry"}


def test_classify_unlabeled_notes_assigns_domain_above_threshold(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            **labeled_notes("chemistry", MIN_CLASS_SIZE),
            **labeled_notes("classical-ml", MIN_CLASS_SIZE),
            "TCP.md": "no frontmatter, no tag -- the untagged note to classify.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    # chemistry notes -> [1, 0], classical-ml notes -> [0, 1]
    vectors = {"TCP": [0.9, 0.1]}
    for i in range(MIN_CLASS_SIZE):
        vectors[f"chemistry note {i}"] = [1.0, 0.0]
        vectors[f"classical-ml note {i}"] = [0.0, 1.0]
    embedder = FakeEmbedder(vectors)

    results = classify_unlabeled_notes(threshold=0.5, _embed_fn=embedder)

    assert len(results) == 1
    assert results[0].note_title == "TCP"
    assert results[0].domain == "chemistry"
    assert results[0].confidence > 0.9


def test_classify_unlabeled_notes_below_threshold_is_excluded(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            **labeled_notes("chemistry", MIN_CLASS_SIZE),
            "Ambiguous.md": "no frontmatter, no tag -- doesn't resemble the one tracked domain.",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    embedder = FakeEmbedder({"Ambiguous": [0.0, 1.0]}, default=[1.0, 0.0])  # orthogonal -> cosine similarity 0.0

    results = classify_unlabeled_notes(threshold=0.5, _embed_fn=embedder)

    assert results == []


def test_classify_unlabeled_notes_no_labeled_domains_returns_empty(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Untagged.md": "no frontmatter, no tag, and nothing else in the vault is tagged either."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    def fail_if_called(texts: list[str]) -> list[list[float]]:
        raise AssertionError("embed_fn should not be called when there are no labeled domains to classify against")

    results = classify_unlabeled_notes(threshold=0.5, _embed_fn=fail_if_called)

    assert results == []


def test_apply_classifications_adds_frontmatter_when_none_exists(tmp_path):
    note_path = tmp_path / "TCP.md"
    note_path.write_text("TCP is a transport protocol.", encoding="utf-8")
    classification = DomainClassification(note_title="TCP", note_path=note_path, domain="networking", confidence=0.8)

    written = apply_classifications([classification])

    assert written == 1
    text = note_path.read_text(encoding="utf-8")
    assert text.startswith("---\ndomain: networking\n---\n\n")
    assert "TCP is a transport protocol." in text


def test_apply_classifications_preserves_existing_frontmatter_keys(tmp_path):
    note_path = tmp_path / "TCP.md"
    note_path.write_text("---\naliases: [Transmission Control Protocol]\n---\nTCP body.", encoding="utf-8")
    classification = DomainClassification(note_title="TCP", note_path=note_path, domain="networking", confidence=0.8)

    apply_classifications([classification])

    text = note_path.read_text(encoding="utf-8")
    assert "aliases: [Transmission Control Protocol]" in text
    assert "domain: networking" in text
    assert "TCP body." in text


def test_apply_classifications_skips_note_that_already_has_a_domain(tmp_path):
    note_path = tmp_path / "TCP.md"
    original = "---\ndomain: existing\n---\nTCP body."
    note_path.write_text(original, encoding="utf-8")
    classification = DomainClassification(note_title="TCP", note_path=note_path, domain="networking", confidence=0.8)

    written = apply_classifications([classification])

    assert written == 0
    assert note_path.read_text(encoding="utf-8") == original
