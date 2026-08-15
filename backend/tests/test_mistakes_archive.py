import json
from datetime import UTC, datetime, timedelta

from learning_os.mistakes import archive, save_mistake, store


def _save(concept: str, domain: str = "classical-ml", confidence: float = 0.5) -> None:
    save_mistake(
        concept=concept,
        explanation="x",
        category="conceptual",
        severity="major",
        confidence=confidence,
        domain=domain,
    )


def test_export_is_written_alongside_the_write(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    _save("Gradient descent")

    exported = json.loads(archive.export_path(db_path).read_text(encoding="utf-8"))
    assert [row["concept"] for row in exported] == ["Gradient descent"]


def test_export_round_trips_losslessly(tmp_path, monkeypatch):
    """The export doubles as a recovery source, so every field has to survive
    the trip — a lossy human-readable rendering would not."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    _save("Gradient descent", confidence=0.87)
    original = store.query_mistakes()[0]

    exported = json.loads(archive.export_path(db_path).read_text(encoding="utf-8"))[0]

    assert exported == original.model_dump(mode="json")


def test_export_ordering_is_stable_regardless_of_insert_order(tmp_path, monkeypatch):
    """Diffability is the point: the same set of mistakes must produce the
    same file, or every commit shows spurious reordering."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    _save("Zebra concept", domain="zoology")
    _save("Alpha concept", domain="algebra")
    first_render = archive.export_path(db_path).read_text(encoding="utf-8")

    reshuffled = list(reversed(store.query_mistakes()))
    archive.write_export(reshuffled, db_path)

    assert archive.export_path(db_path).read_text(encoding="utf-8") == first_render


def test_first_write_creates_a_backup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    _save("Gradient descent")

    assert len(list(archive.backups_dir(db_path).glob("test-*.db"))) == 1


def test_second_write_same_day_does_not_pile_up_backups(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    _save("Gradient descent")
    _save("Optimizer")

    assert len(list(archive.backups_dir(db_path).glob("test-*.db"))) == 1


def test_backup_is_due_again_once_the_interval_has_passed(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    _save("Gradient descent")

    tomorrow = datetime.now(UTC) + archive.BACKUP_INTERVAL + timedelta(minutes=1)
    archive.backup_database(db_path, now=tomorrow)

    assert len(list(archive.backups_dir(db_path).glob("test-*.db"))) == 2


def test_backup_contains_the_real_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    _save("Gradient descent")

    backup = archive.backup_database(db_path, force=True)

    # Point the store at the backup itself and read it back: proves the copy
    # is a real, openable database, not just a file of the right size.
    monkeypatch.setenv("DB_PATH", str(backup))
    store.get_settings.cache_clear()

    assert [m.concept for m in store.query_mistakes()] == ["Gradient descent"]


def test_rotation_keeps_only_the_most_recent(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    _save("Gradient descent")

    start = datetime.now(UTC)
    for day in range(1, archive.BACKUPS_TO_KEEP + 5):
        archive.backup_database(db_path, force=True, now=start + timedelta(days=day))

    assert len(list(archive.backups_dir(db_path).glob("test-*.db"))) == archive.BACKUPS_TO_KEEP


def test_archive_failure_does_not_lose_the_mistake(tmp_path, monkeypatch, capsys):
    """The row is already committed when the archive runs; a broken export
    must not take the session down with it — but it must be visible."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(archive, "write_export", boom)
    _save("Gradient descent")

    assert [m.concept for m in store.query_mistakes()] == ["Gradient descent"]
    assert "export/backup failed" in capsys.readouterr().err
