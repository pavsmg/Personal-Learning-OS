import re
from pathlib import Path

from learning_os.config import get_settings
from learning_os.language.models import MistakePattern, PracticeLogEntry

MISTAKE_ENTRY_RE = re.compile(
    r"^- \*\*(?P<pattern>.+?)\*\* \(seen (?P<count>\d+)x\) — (?P<description>.+?) Status: (?P<status>\w+)\s*$"
)
CATEGORY_HEADER_RE = re.compile(r"^## (.+)$")
LOG_HEADER_RE = re.compile(r"^### (?P<date>\d{4}-\d{2}-\d{2}) — (?P<focus>.+)$")
ROADMAP_LINE_RE = re.compile(r"^- \d+\.\s*(?P<section>.+?)\s*—\s*(?P<status>.+)$")


def language_dir(language: str) -> Path:
    return get_settings().language_lab_path / "languages" / language.lower()


def parse_mistakes(text: str) -> list[MistakePattern]:
    entries = []
    current_category = "General"
    for line in text.splitlines():
        header_match = CATEGORY_HEADER_RE.match(line)
        if header_match:
            current_category = header_match.group(1).strip()
            continue
        entry_match = MISTAKE_ENTRY_RE.match(line)
        if entry_match:
            entries.append(
                MistakePattern(
                    category=current_category,
                    pattern=entry_match.group("pattern"),
                    seen_count=int(entry_match.group("count")),
                    status=entry_match.group("status"),
                    description=entry_match.group("description"),
                )
            )
    return entries


def parse_practice_log(text: str) -> list[PracticeLogEntry]:
    entries = []
    current: tuple[str, str] | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current is not None:
            entries.append(PracticeLogEntry(date=current[0], focus=current[1], raw="\n".join(buffer).strip()))

    for line in text.splitlines():
        match = LOG_HEADER_RE.match(line)
        if match:
            flush()
            current = (match.group("date"), match.group("focus"))
            buffer = []
        elif current is not None:
            buffer.append(line)
    flush()
    return entries


def parse_roadmap(text: str) -> list[str]:
    results = []
    for line in text.splitlines():
        match = ROADMAP_LINE_RE.match(line)
        if match:
            results.append(f"{match.group('section')} — {match.group('status')}")
    return results
