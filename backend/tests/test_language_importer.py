from learning_os.language.importer import import_all_languages, import_language_mistakes
from learning_os.mistakes.service import get_learning_profile

MISTAKES_FIXTURE = """\
## Grammar

- **subject-verb agreement** (seen 2x) — said "he go" instead of "he goes". Status: Active
- **article omission** (seen 1x) — dropped "the". Status: Watching

## Vocabulary

- **false friend** (seen 3x) — confused two words. Status: Resolved
"""


def set_env(monkeypatch, tmp_path, language_lab_root):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LANGUAGE_LAB_PATH", str(language_lab_root))


def make_language_lab(tmp_path, language: str, mistakes_text: str | None = None):
    lang_dir = tmp_path / "language_lab" / "languages" / language
    lang_dir.mkdir(parents=True)
    if mistakes_text is not None:
        (lang_dir / "MISTAKES.md").write_text(mistakes_text, encoding="utf-8")
    return tmp_path / "language_lab"


def test_import_language_mistakes_maps_status_to_confidence_and_severity(tmp_path, monkeypatch):
    root = make_language_lab(tmp_path, "testlang", MISTAKES_FIXTURE)
    set_env(monkeypatch, tmp_path, root)

    count = import_language_mistakes("testlang")

    assert count == 3
    profile = {m.concept: m for m in get_learning_profile(domain="testlang")}
    assert set(profile.keys()) == {"subject-verb agreement", "article omission", "false friend"}
    # Active (0.7 confidence) + seen 2x -> moderate severity
    assert profile["subject-verb agreement"].mistake_count == 1


def test_import_language_mistakes_is_idempotent(tmp_path, monkeypatch):
    root = make_language_lab(tmp_path, "testlang", MISTAKES_FIXTURE)
    set_env(monkeypatch, tmp_path, root)

    first = import_language_mistakes("testlang")
    second = import_language_mistakes("testlang")

    assert first == 3
    assert second == 0  # already imported, no duplicates
    assert len(get_learning_profile(domain="testlang")) == 3


def test_import_language_mistakes_no_mistakes_file_returns_zero(tmp_path, monkeypatch):
    root = make_language_lab(tmp_path, "empty_lang", mistakes_text=None)
    set_env(monkeypatch, tmp_path, root)

    assert import_language_mistakes("empty_lang") == 0


def test_import_all_languages_returns_per_language_counts(tmp_path, monkeypatch):
    root = tmp_path / "language_lab"
    (root / "languages" / "english").mkdir(parents=True)
    (root / "languages" / "english" / "MISTAKES.md").write_text(MISTAKES_FIXTURE, encoding="utf-8")
    for lang in ("german", "japanese", "turkish"):
        (root / "languages" / lang).mkdir(parents=True)
    set_env(monkeypatch, tmp_path, root)

    counts = import_all_languages()

    assert counts["english"] == 3
    assert counts["german"] == 0
    assert counts["japanese"] == 0
    assert counts["turkish"] == 0
