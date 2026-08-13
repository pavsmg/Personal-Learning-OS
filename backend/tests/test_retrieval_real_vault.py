from pathlib import Path

import pytest

from learning_os.retrieval.loader import load_vault
from learning_os.retrieval.service import concept_importance, get_note, related_notes, search_notes

REAL_VAULT_PATH = Path("~/Documents/Obsidian-Digital-Brain").expanduser()

pytestmark = pytest.mark.skipif(
    not REAL_VAULT_PATH.exists(),
    reason="Real Obsidian vault not present on this machine",
)


@pytest.fixture(autouse=True)
def _point_at_real_vault(monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(REAL_VAULT_PATH))


def test_ai_ml_domain_get_note_adam_optimizer():
    note = get_note("Adam optimizer")

    assert note is not None
    assert note.frontmatter.get("domain") == "classical-ml"
    assert "gradient descent" in [link.lower() for link in note.outgoing_links]


def test_ai_ml_domain_related_notes_bidirectional():
    related_from_adam = [r.title.lower() for r in related_notes("Adam optimizer")]
    related_from_gradient_descent = [r.title.lower() for r in related_notes("Gradient descent")]

    assert "gradient descent" in related_from_adam
    assert "adam optimizer" in related_from_gradient_descent


def test_ai_ml_domain_search_ranks_gradient_descent_near_top():
    results = search_notes("gradient descent")

    assert results
    assert results[0].title.lower() == "gradient descent"


def test_language_domain_get_note_turkish_roadmap():
    note = get_note("TURKISH ROADMAP")

    assert note is not None
    assert "vowel harmony" in [link.lower() for link in note.outgoing_links]


def test_language_domain_related_notes_turkish_alphabet():
    related = [r.title.lower() for r in related_notes("Turkish alphabet")]

    assert "turkish roadmap" in related
    assert "turkish study plan" in related


def test_language_domain_search_turkish():
    results = search_notes("turkish")

    assert any(r.title.lower() == "turkish roadmap" for r in results)


def test_search_no_match_returns_empty():
    assert search_notes("xqzzptmnvbklw") == []


def test_get_note_not_found_returns_none():
    assert get_note("does not exist") is None


def test_vault_loaded_more_than_a_thousand_notes():
    notes = load_vault(REAL_VAULT_PATH)

    assert len(notes) > 1000


def test_ai_ml_domain_concept_importance_tcp_is_positive():
    assert concept_importance("TCP") > 0


def test_concept_importance_unknown_concept_returns_zero():
    assert concept_importance("xqzzptmnvbklw") == 0
