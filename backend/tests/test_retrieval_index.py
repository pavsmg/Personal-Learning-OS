from pathlib import Path

from learning_os.retrieval.index import VaultIndex
from learning_os.retrieval.models import Note


def make_note(title: str, body: str = "", tags: list[str] | None = None, links: list[str] | None = None) -> Note:
    return Note(
        title=title,
        path=Path(f"/vault/{title}.md"),
        frontmatter={},
        tags=tags or [],
        body=body,
        outgoing_links=links or [],
    )


def build_index(*notes: Note) -> VaultIndex:
    return VaultIndex({note.title.lower(): note for note in notes})


def test_search_title_match_ranks_above_body_only_match():
    title_hit = make_note("Gradient descent", body="an optimization method")
    body_only_hit = make_note("Adam optimizer", body="builds on gradient descent")
    index = build_index(title_hit, body_only_hit)

    results = index.search("gradient descent")

    assert [r.title for r in results][0] == "Gradient descent"


def test_search_is_case_insensitive():
    index = build_index(make_note("Gradient descent"))

    assert [r.title for r in index.search("GRADIENT DESCENT")] == ["Gradient descent"]


def test_search_empty_query_returns_empty():
    index = build_index(make_note("Gradient descent"))

    assert index.search("") == []


def test_search_no_match_returns_empty():
    index = build_index(make_note("Gradient descent"))

    assert index.search("nonexistent-gibberish-xyz") == []


def test_search_limit_truncates_results():
    notes = [make_note(f"Note {i}", body="shared keyword") for i in range(5)]
    index = build_index(*notes)

    assert len(index.search("shared", limit=2)) == 2


def test_get_is_case_insensitive_and_whitespace_tolerant():
    index = build_index(make_note("Gradient descent"))

    assert index.get("  GRADIENT DESCENT  ").title == "Gradient descent"


def test_get_not_found_returns_none():
    index = build_index(make_note("Gradient descent"))

    assert index.get("does not exist") is None


def test_related_is_bidirectional():
    a = make_note("A", links=["B"])
    b = make_note("B")
    index = build_index(a, b)

    assert [r.title for r in index.related("A")] == ["B"]
    assert [r.title for r in index.related("B")] == ["A"]


def test_related_excludes_dangling_links():
    a = make_note("A", links=["Nonexistent"])
    index = build_index(a)

    assert index.related("A") == []


def test_related_excludes_self_reference():
    a = make_note("A", links=["A"])
    index = build_index(a)

    assert index.related("A") == []


def test_related_isolated_note_returns_empty():
    a = make_note("A")
    index = build_index(a)

    assert index.related("A") == []


def test_related_not_found_returns_empty():
    index = build_index(make_note("A"))

    assert index.related("does not exist") == []
