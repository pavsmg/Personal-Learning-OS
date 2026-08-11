from pathlib import Path

import pytest

from learning_os.language.importer import import_language_mistakes
from learning_os.language.loader import parse_mistakes
from learning_os.mistakes.service import get_learning_profile

REAL_LANGUAGE_LAB_PATH = Path("~/Projects/Language-Lab").expanduser()

pytestmark = pytest.mark.skipif(
    not REAL_LANGUAGE_LAB_PATH.exists(),
    reason="Real Language-Lab checkout not present on this machine",
)


def test_parse_mistakes_against_real_english_data():
    mistakes_path = REAL_LANGUAGE_LAB_PATH / "languages" / "english" / "MISTAKES.md"
    entries = parse_mistakes(mistakes_path.read_text(encoding="utf-8"))

    assert len(entries) == 6
    assert {e.category for e in entries} == {
        "Grammar",
        "Prepositions & Articles",
        "Vocabulary & False Friends",
        "Idiomatic / Naturalness",
    }


def test_import_real_english_data_into_isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LANGUAGE_LAB_PATH", str(REAL_LANGUAGE_LAB_PATH))

    count = import_language_mistakes("english")

    assert count == 6
    profile = get_learning_profile(domain="english")
    assert len(profile) == 6
    confidences = {round(m.conceptual_understanding, 2) for m in profile}
    # All real English entries are "Watching" (confidence 0.4 -> understanding 0.6)
    assert confidences == {0.6}


def test_import_empty_template_languages_return_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LANGUAGE_LAB_PATH", str(REAL_LANGUAGE_LAB_PATH))

    for language in ("german", "japanese", "turkish"):
        assert import_language_mistakes(language) == 0
