"""Durability for the mistake store, per decisions.md #10: a git-tracked,
human-readable JSON export written alongside every write, plus a rotating
binary backup of the .db itself.

Every path here derives from db_path rather than from its own setting, so a
redirected database (tests, a second vault, a scratch copy) can never write
into the real repo's export or backup directory. That is the whole reason
these are functions of db_path instead of module constants.
"""

import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from learning_os.mistakes.models import Evidence, MistakeEntry

BACKUP_INTERVAL = timedelta(days=1)
BACKUPS_TO_KEEP = 10
_BACKUP_STAMP = "%Y%m%dT%H%M%SZ"


def export_path(db_path: Path) -> Path:
    return db_path.with_name(f"{db_path.stem}_export.json")


def evidence_export_path(db_path: Path) -> Path:
    """A second, separate flat file rather than merging into export_path's
    output -- keeps MistakeEntry's export format (and its lossless
    round-trip test) untouched by an unrelated table's schema."""
    return db_path.with_name(f"{db_path.stem}_evidence_export.json")


def backups_dir(db_path: Path) -> Path:
    return db_path.parent / "backups"


def _sort_key(entry: MistakeEntry) -> tuple[str, str, str]:
    return (entry.timestamp.isoformat(), entry.domain.lower(), entry.concept.lower())


def write_export(entries: list[MistakeEntry], db_path: Path) -> Path:
    """Lossless, deterministically ordered JSON. Lossless matters twice over:
    it is the diffable audit trail #10 asked for, and because every field
    survives the round trip it doubles as a recovery source if the binary
    store is lost — which a Markdown rendering would not.

    The whole file is rewritten per write rather than appended to. At this
    scale (tens of rows) that costs nothing and keeps the file consistent
    with the database by construction; if the store ever grows to where that
    hurts, that is the moment to revisit, not now.
    """
    path = export_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [entry.model_dump(mode="json") for entry in sorted(entries, key=_sort_key)]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _evidence_sort_key(entry: Evidence) -> tuple[str, str, str]:
    return (entry.timestamp.isoformat(), entry.domain.lower(), entry.concept.lower())


def write_evidence_export(entries: list[Evidence], db_path: Path) -> Path:
    """Same lossless/deterministic/whole-file-rewrite shape as write_export,
    kept as a genuinely separate function (not a generic merge) so a future
    change to either table's export format can't accidentally couple to
    the other's."""
    path = evidence_export_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [entry.model_dump(mode="json") for entry in sorted(entries, key=_evidence_sort_key)]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _existing_backups(db_path: Path) -> list[Path]:
    return sorted(backups_dir(db_path).glob(f"{db_path.stem}-*.db"))


def _prune_backups(db_path: Path) -> None:
    for stale in _existing_backups(db_path)[:-BACKUPS_TO_KEEP]:
        stale.unlink()


def _is_due(db_path: Path, now: datetime) -> bool:
    existing = _existing_backups(db_path)
    if not existing:
        return True
    newest = datetime.fromtimestamp(existing[-1].stat().st_mtime, UTC)
    return now - newest >= BACKUP_INTERVAL


def backup_database(db_path: Path, force: bool = False, now: datetime | None = None) -> Path | None:
    """Timestamped copy via SQLite's own backup API, not shutil.copy: the
    live connection may be mid-write, and only the native API is guaranteed
    to produce a consistent snapshot of it. Returns None when a backup was
    taken recently enough (BACKUP_INTERVAL) and force is not set — no new
    data, no new backup.
    """
    if not db_path.exists():
        return None

    moment = now or datetime.now(UTC)
    if not force and not _is_due(db_path, moment):
        return None

    destination = backups_dir(db_path) / f"{db_path.stem}-{moment.strftime(_BACKUP_STAMP)}.db"
    destination.parent.mkdir(parents=True, exist_ok=True)

    source = sqlite3.connect(db_path)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    _prune_backups(db_path)
    return destination


def after_write(entries: list[MistakeEntry], db_path: Path) -> None:
    """Called once per store write. Deliberately swallows its own failures:
    the mistake is already committed at this point, and losing the audit
    copy is bad, but crashing a live tutoring session after the data is
    safely stored is worse. It reports on stderr rather than failing
    silently, so a broken export is noticed rather than assumed working.
    """
    try:
        write_export(entries, db_path)
        backup_database(db_path)
    except Exception as exc:  # noqa: BLE001 — durability is best-effort, the write itself already succeeded
        print(f"[archive] export/backup failed: {exc}", file=sys.stderr)


def after_evidence_write(entries: list[Evidence], db_path: Path) -> None:
    """evidence's counterpart to after_write. No second backup_database
    call: sqlite3's native backup snapshots the whole .db file, which
    already covers the evidence table living in the same database."""
    try:
        write_evidence_export(entries, db_path)
        backup_database(db_path)
    except Exception as exc:  # noqa: BLE001 — durability is best-effort, the write itself already succeeded
        print(f"[archive] evidence export/backup failed: {exc}", file=sys.stderr)
