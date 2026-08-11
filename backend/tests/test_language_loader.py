from learning_os.language.loader import parse_mistakes, parse_practice_log, parse_roadmap

MISTAKES_FIXTURE = """\
# Recurring Mistakes / Focus Areas — Test

Entry format: `- **topic** (seen Nx) — description. Status: Active/Watching/Resolved`

## Grammar

- **subject-verb agreement** (seen 2x) — e.g. said "he go" instead of "he goes". Status: Active
- **article omission** (seen 1x) — dropped "the" before a specific noun. Status: Watching

## Vocabulary

- **false friend: actual/actual** (seen 3x) — confused "actual" with "current". Status: Resolved

## Pronunciation
"""

PRACTICE_LOG_FIXTURE = """\
# Practice Log — Test

Entry format:

```
### YYYY-MM-DD — Session focus
- Type: New | Review
```

### 2026-08-01 — First session
- Type: New
- Went well: introduced basics.

### 2026-08-05 — Second session
- Type: Review
- Went well: fewer mistakes.
"""

ROADMAP_FIXTURE = """\
# Practice Roadmap — Test

- 1. Basics — In progress (some notes)
- 2. Intermediate — Not started
"""


def test_parse_mistakes_extracts_entries_with_categories():
    entries = parse_mistakes(MISTAKES_FIXTURE)

    assert len(entries) == 3
    assert entries[0].category == "Grammar"
    assert entries[0].pattern == "subject-verb agreement"
    assert entries[0].seen_count == 2
    assert entries[0].status == "Active"
    assert entries[2].category == "Vocabulary"
    assert entries[2].status == "Resolved"


def test_parse_mistakes_empty_category_produces_no_entries():
    entries = parse_mistakes(MISTAKES_FIXTURE)

    assert not any(e.category == "Pronunciation" for e in entries)


def test_parse_mistakes_malformed_lines_skipped():
    text = "## Grammar\n- this is not a properly formatted entry\n- **pattern** missing the rest\n"

    assert parse_mistakes(text) == []


def test_parse_mistakes_empty_file_returns_empty_list():
    assert parse_mistakes("") == []
    assert parse_mistakes("No sessions logged yet.\n") == []


def test_parse_practice_log_extracts_entries_with_raw_text():
    entries = parse_practice_log(PRACTICE_LOG_FIXTURE)

    assert len(entries) == 2
    assert entries[0].date == "2026-08-01"
    assert entries[0].focus == "First session"
    assert "introduced basics" in entries[0].raw
    assert entries[1].date == "2026-08-05"


def test_parse_practice_log_empty_file_returns_empty_list():
    assert parse_practice_log("") == []


def test_parse_roadmap_extracts_section_status_lines():
    lines = parse_roadmap(ROADMAP_FIXTURE)

    assert lines == ["Basics — In progress (some notes)", "Intermediate — Not started"]


def test_parse_roadmap_no_matching_lines_returns_empty_list():
    assert parse_roadmap("No sessions logged yet — status is Not started across the board.\n") == []
