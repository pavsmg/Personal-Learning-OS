from pathlib import Path

from learning_os.retrieval.loader import (
    extract_links,
    extract_tags,
    iter_markdown_files,
    load_note,
    load_vault,
    parse_frontmatter,
)


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_frontmatter_valid():
    frontmatter, body = parse_frontmatter("---\ndomain: classical-ml\n---\nbody text\n")

    assert frontmatter == {"domain": "classical-ml"}
    assert body == "body text\n"


def test_parse_frontmatter_absent():
    text = "## Heading\nno frontmatter here\n"

    frontmatter, body = parse_frontmatter(text)

    assert frontmatter == {}
    assert body == text


def test_parse_frontmatter_dash_used_as_horizontal_rule_with_no_closing_pair():
    text = "---\n- a point\n- another point\n"

    frontmatter, body = parse_frontmatter(text)

    assert frontmatter == {}
    assert body == text


def test_parse_frontmatter_malformed_yaml_falls_back():
    text = "---\n[unclosed: [\n---\nbody\n"

    frontmatter, body = parse_frontmatter(text)

    assert frontmatter == {}
    assert body == text


def test_parse_frontmatter_non_dict_yaml_falls_back():
    text = "---\n- one\n- two\n---\nbody\n"

    frontmatter, body = parse_frontmatter(text)

    assert frontmatter == {}
    assert body == text


def test_extract_links_piped_alias_resolves_to_target():
    assert extract_links("See [[Gradient descent|GD]] for details.") == ["Gradient descent"]


def test_extract_links_excludes_image_embeds():
    assert extract_links("![[diagram.png | 400]]") == []


def test_extract_links_excludes_non_embed_image_extension():
    assert extract_links("[[diagram.png]]") == []


def test_extract_links_keeps_dangling_targets():
    assert extract_links("[[Nonexistent Concept]]") == ["Nonexistent Concept"]


def test_extract_links_dedupes_case_insensitively_preserving_first_seen():
    assert extract_links("[[Gradient descent]] and [[GRADIENT DESCENT]]") == ["Gradient descent"]


def test_extract_tags_own_line_extracted():
    assert extract_tags("some body\n#fitness\n") == ["fitness"]


def test_extract_tags_heading_not_extracted():
    assert extract_tags("## Fitness Notes\nbody\n") == []


def test_extract_tags_digit_leading_not_extracted():
    assert extract_tags("see point #123 above\n") == []


def test_load_note_body_level_keywords_line_never_treated_as_frontmatter(tmp_path):
    note_path = write(tmp_path / "Template style.md", "KEYWORDS: something\nSUMMARY: something else\n")

    note = load_note(note_path)

    assert note.frontmatter == {}
    assert "KEYWORDS: something" in note.body


def test_load_note_in_subfolder_keyed_by_stem_only(tmp_path):
    subfolder = tmp_path / "Physics"
    subfolder.mkdir()
    note_path = write(subfolder / "Entropy.md", "body\n")

    note = load_note(note_path)

    assert note.title == "Entropy"


def test_load_note_non_ascii_filename_and_content(tmp_path):
    note_path = write(tmp_path / "Café.md", "Café is a [[Beverage]].\n")

    note = load_note(note_path)

    assert note.title == "Café"
    assert "Café" in note.body


def test_load_note_zero_byte_file(tmp_path):
    note_path = write(tmp_path / "Untitled.md", "")

    note = load_note(note_path)

    assert note.frontmatter == {}
    assert note.tags == []
    assert note.body == ""
    assert note.outgoing_links == []


def test_iter_markdown_files_skips_dot_directories(tmp_path):
    (tmp_path / ".obsidian").mkdir()
    write(tmp_path / ".obsidian" / "workspace.md", "should be skipped\n")
    write(tmp_path / "Real note.md", "kept\n")

    found = {path.name for path in iter_markdown_files(tmp_path)}

    assert found == {"Real note.md"}


def test_load_vault_skips_dot_directories_and_keys_by_lowercase_title(tmp_path):
    (tmp_path / ".git").mkdir()
    write(tmp_path / ".git" / "ignored.md", "ignored\n")
    write(tmp_path / "Gradient descent.md", "core concept\n")

    notes = load_vault(tmp_path)

    assert set(notes.keys()) == {"gradient descent"}
