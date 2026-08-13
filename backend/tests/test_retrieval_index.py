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


def test_search_exact_title_match_ranks_above_substring_title_match():
    exact = make_note("TCP", body="core protocol")
    substring = make_note("TCP-IP", body="protocol suite")
    index = build_index(exact, substring)

    results = index.search("TCP")

    assert [r.title for r in results][0] == "TCP"


def test_search_length_normalization_favors_concentrated_short_note():
    # Same term, same raw occurrence count is *not* what's being tested --
    # the long note repeats the term more times in absolute terms but is
    # heavily diluted by unrelated filler; the short, focused note should
    # still win once term frequency is normalized against document length.
    short_focused = make_note("Short", body="keyword keyword keyword")
    long_diluted = make_note("Long", body=("keyword " * 9) + ("filler word " * 200))
    index = build_index(short_focused, long_diluted)

    results = index.search("keyword")

    assert [r.title for r in results][0] == "Short"


def test_search_idf_discounts_common_terms_relative_to_rare_ones():
    # "common" appears in 3 of 4 notes' bodies; "rare" appears in only 1.
    # Both matching notes have identical term frequency and body length --
    # the only difference is how common each term is across the corpus.
    matches_common_term = make_note("MatchesCommon", body="common")
    matches_rare_term = make_note("MatchesRare", body="rare")
    filler1 = make_note("Filler1", body="common")
    filler2 = make_note("Filler2", body="common")
    index = build_index(matches_common_term, matches_rare_term, filler1, filler2)

    results = index.search("common rare")

    assert [r.title for r in results][0] == "MatchesRare"


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


def test_importance_returns_backlink_count_for_real_note():
    hub = make_note("Hub")
    a = make_note("A", links=["Hub"])
    b = make_note("B", links=["Hub"])
    index = build_index(hub, a, b)

    assert index.importance("Hub") == 2


def test_importance_is_case_insensitive_and_whitespace_tolerant():
    hub = make_note("Hub")
    a = make_note("A", links=["Hub"])
    index = build_index(hub, a)

    assert index.importance("  HUB  ") == 1


def test_importance_unknown_title_returns_zero():
    index = build_index(make_note("Gradient descent"))

    assert index.importance("does not exist") == 0


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


def test_related_ranks_mutual_above_outgoing_only_above_incoming_only():
    # A <-> Mutual (linked both ways): strongest signal.
    # A -> OutOnly (A links out, nothing links back).
    # InOnly -> A (something links to A, A doesn't link back): weakest.
    a = make_note("A", links=["Mutual", "OutOnly"])
    mutual = make_note("Mutual", links=["A"])
    out_only = make_note("OutOnly")
    in_only = make_note("InOnly", links=["A"])
    index = build_index(a, mutual, out_only, in_only)

    assert [r.title for r in index.related("A")] == ["Mutual", "OutOnly", "InOnly"]


def test_related_sorts_alphabetically_within_each_tier():
    a = make_note("A", links=["Zeta", "Alpha"])
    zeta = make_note("Zeta")
    alpha = make_note("Alpha")
    index = build_index(a, zeta, alpha)

    assert [r.title for r in index.related("A")] == ["Alpha", "Zeta"]


def test_related_ranks_by_backlink_count_within_tier():
    # Alpha and Zeta are both incoming-only neighbors of A. Alpha sorts
    # first alphabetically but has zero backlinks of its own; Zeta sorts
    # last alphabetically but is linked to by Extra, giving it one
    # backlink. Zeta should rank first -- this could not pass under pure
    # alphabetical ordering.
    a = make_note("A")
    alpha = make_note("Alpha", links=["A"])
    zeta = make_note("Zeta", links=["A"])
    extra = make_note("Extra", links=["Zeta"])
    index = build_index(a, alpha, zeta, extra)

    assert [r.title for r in index.related("A")] == ["Zeta", "Alpha"]


def test_most_important_ranks_by_backlink_count_descending():
    hub = make_note("Hub")
    a = make_note("A", links=["Hub"])
    b = make_note("B", links=["Hub"])
    c = make_note("C", links=["Hub"])
    leaf = make_note("Leaf")
    index = build_index(hub, a, b, c, leaf)

    results = index.most_important(limit=5)

    assert results[0].title == "Hub"


def test_most_important_respects_limit():
    notes = [make_note(f"Note {i}") for i in range(5)]
    index = build_index(*notes)

    assert len(index.most_important(limit=2)) == 2


def test_most_important_empty_vault_returns_empty():
    index = build_index()

    assert index.most_important() == []
