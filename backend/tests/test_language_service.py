import pytest

from learning_os.language.importer import import_language_mistakes
from learning_os.language.service import get_curriculum, get_language_profile, retrieve_vocabulary

MISTAKES_FIXTURE = """\
## Grammar

- **subject-verb agreement** (seen 2x) — said "he go". Status: Active
"""

ROADMAP_FIXTURE = """\
- 1. Basics — In progress
"""

PRACTICE_LOG_FIXTURE = """\
### 2026-08-01 — First session
- Went well: good start.
"""


def set_env(monkeypatch, tmp_path, language_lab_root):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LANGUAGE_LAB_PATH", str(language_lab_root))


def make_language_lab(tmp_path, language: str, mistakes=None, roadmap=None, practice_log=None):
    lang_dir = tmp_path / "language_lab" / "languages" / language
    lang_dir.mkdir(parents=True)
    if mistakes is not None:
        (lang_dir / "MISTAKES.md").write_text(mistakes, encoding="utf-8")
    if roadmap is not None:
        (lang_dir / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    if practice_log is not None:
        (lang_dir / "PRACTICE_LOG.md").write_text(practice_log, encoding="utf-8")
    return tmp_path / "language_lab"


def test_get_language_profile_unknown_language_raises_value_error(tmp_path, monkeypatch):
    root = make_language_lab(tmp_path, "testlang")
    set_env(monkeypatch, tmp_path, root)

    with pytest.raises(ValueError):
        get_language_profile("does-not-exist")


def test_get_curriculum_unknown_language_raises_value_error(tmp_path, monkeypatch):
    root = make_language_lab(tmp_path, "testlang")
    set_env(monkeypatch, tmp_path, root)

    with pytest.raises(ValueError):
        get_curriculum("does-not-exist")


def test_get_language_profile_combines_mastery_practice_and_roadmap(tmp_path, monkeypatch):
    root = make_language_lab(
        tmp_path, "testlang", mistakes=MISTAKES_FIXTURE, roadmap=ROADMAP_FIXTURE, practice_log=PRACTICE_LOG_FIXTURE
    )
    set_env(monkeypatch, tmp_path, root)
    import_language_mistakes("testlang")

    profile = get_language_profile("testlang")

    assert profile["language"] == "testlang"
    assert len(profile["mastery"]) == 1
    assert profile["mastery"][0]["concept"] == "subject-verb agreement"
    assert profile["roadmap_status"] == ["Basics — In progress"]
    assert len(profile["recent_practice"]) == 1
    assert profile["recent_practice"][0]["date"] == "2026-08-01"


def test_get_language_profile_empty_language_has_empty_mastery(tmp_path, monkeypatch):
    root = make_language_lab(tmp_path, "testlang")
    set_env(monkeypatch, tmp_path, root)

    profile = get_language_profile("testlang")

    assert profile["mastery"] == []
    assert profile["recent_practice"] == []
    assert profile["roadmap_status"] == []


def test_get_curriculum_returns_parsed_roadmap(tmp_path, monkeypatch):
    root = make_language_lab(tmp_path, "testlang", roadmap=ROADMAP_FIXTURE)
    set_env(monkeypatch, tmp_path, root)

    assert get_curriculum("testlang") == ["Basics — In progress"]


def test_retrieve_vocabulary_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        retrieve_vocabulary("english")
