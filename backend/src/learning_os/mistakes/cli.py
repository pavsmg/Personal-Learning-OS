import argparse

from learning_os.config import get_settings
from learning_os.mistakes import archive, store


def run() -> None:
    """Forces a backup and rewrites the export now. The write-triggered path
    in store.py only fires when there is new data, which is exactly when a
    backup is least needed; this is the entry point for a real periodic
    schedule (cron, systemd timer) per decisions.md #10.
    """
    parser = argparse.ArgumentParser(description="Back up the mistake database and refresh its git-tracked export.")
    parser.add_argument("--export-only", action="store_true", help="Rewrite the JSON export without a new backup.")
    args = parser.parse_args()

    db_path = get_settings().db_path
    entries = store.query_mistakes()
    export = archive.write_export(entries, db_path)
    print(f"Exported {len(entries)} mistakes to {export}")

    if args.export_only:
        return

    backup = archive.backup_database(db_path, force=True)
    if backup is None:
        print(f"No database at {db_path} — nothing to back up.")
    else:
        kept = len(sorted(archive.backups_dir(db_path).glob(f"{db_path.stem}-*.db")))
        print(f"Backed up to {backup} ({kept} of {archive.BACKUPS_TO_KEEP} kept)")
