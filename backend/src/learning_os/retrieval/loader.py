import os
import re
from pathlib import Path

import yaml

from learning_os.retrieval.models import Note

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"(!?)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
TAG_RE = re.compile(r"(?<![\w#])#([a-z][a-z0-9_-]*)\b")
HEADING_RE = re.compile(r"^#{1,6}\s")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".pdf"}


def iter_markdown_files(vault_path: Path):
    for dirpath, dirnames, filenames in os.walk(vault_path):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if name.endswith(".md"):
                yield Path(dirpath) / name


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, text
    if not isinstance(data, dict):
        return {}, text
    return data, text[match.end():]


def extract_links(body: str) -> list[str]:
    targets = []
    for is_embed, target in WIKILINK_RE.findall(body):
        target = target.strip()
        if is_embed or not target:
            continue
        if Path(target).suffix.lower() in IMAGE_EXTENSIONS:
            continue
        targets.append(target)

    seen: set[str] = set()
    result = []
    for target in targets:
        if target.lower() not in seen:
            seen.add(target.lower())
            result.append(target)
    return result


def extract_tags(body: str) -> list[str]:
    tags = []
    for line in body.splitlines():
        if HEADING_RE.match(line):
            continue
        tags.extend(TAG_RE.findall(line))

    seen: set[str] = set()
    result = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def load_note(path: Path) -> Note:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    return Note(
        title=path.stem,
        path=path.resolve(),
        frontmatter=frontmatter,
        tags=extract_tags(body),
        body=body.strip(),
        outgoing_links=extract_links(body),
    )


def load_vault(vault_path: Path) -> dict[str, Note]:
    notes: dict[str, Note] = {}
    for path in iter_markdown_files(vault_path):
        try:
            note = load_note(path)
        except Exception:
            continue
        notes[note.title.lower()] = note
    return notes
