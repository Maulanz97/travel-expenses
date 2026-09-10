"""Clear test data, or explicitly rebuild the local database from current migrations."""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path


TABLES_TO_CLEAR = (
    "payments",
    "expense_participants",
    "expenses",
    "group_members",
    "groups",
    "users",
)


def get_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        for table in TABLES_TO_CLEAR
    }


def validate_schema(connection: sqlite3.Connection) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    missing = set(TABLES_TO_CLEAR) - tables
    if missing:
        raise RuntimeError(
            f"The database is missing expected tables: {', '.join(sorted(missing))}"
        )


def create_backup(database_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = database_path.with_name(
        f"{database_path.stem}-{timestamp}.db.bak"
    )
    source = sqlite3.connect(database_path)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    return backup_path


def clear_data(database_path: Path) -> tuple[Path, dict[str, int]]:
    backup_path = create_backup(database_path)
    connection = sqlite3.connect(database_path, timeout=10)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        validate_schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        for table in TABLES_TO_CLEAR:
            connection.execute(f"DELETE FROM {table}")
        connection.commit()
        return backup_path, get_counts(connection)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def rebuild_database(database_path: Path):
    """Build a fresh schema first, then atomically copy it into the local database."""
    from alembic import command
    from alembic.config import Config
    root = Path(__file__).resolve().parents[1]
    if database_path.resolve() != root / 'expenses.db':
        raise RuntimeError('Schema rebuild is restricted to backend/expenses.db.')
    with tempfile.TemporaryDirectory() as directory:
        fresh = Path(directory) / 'fresh.db'
        config = Config(str(root / 'alembic.ini'))
        config.set_main_option('script_location', str(root / 'alembic'))
        config.set_main_option('sqlalchemy.url', f'sqlite:///{fresh.as_posix()}')
        command.upgrade(config, 'head')
        backup = create_backup(database_path) if database_path.exists() else None
        with closing(sqlite3.connect(fresh)) as source, closing(sqlite3.connect(database_path)) as target:
            source.backup(target)
        print(f'Fresh database ready. Previous backup: {backup}')


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clear local test data while preserving the SQLite schema."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "expenses.db",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required to create a backup and delete the test records.",
    )
    parser.add_argument('--rebuild', action='store_true', help='Recreate the local schema from the consolidated migration; requires --confirm.')
    arguments = parser.parse_args()
    database_path = arguments.database.resolve()
    if arguments.rebuild:
        if not arguments.confirm:
            parser.error('--rebuild requires --confirm; all local records will be removed.')
        rebuild_database(database_path)
        return 0
    if not database_path.is_file():
        print(f"Database not found: {database_path}", file=sys.stderr)
        return 1

    with sqlite3.connect(database_path) as connection:
        validate_schema(connection)
        counts = get_counts(connection)
    print("Current records:")
    for table, count in counts.items():
        print(f"  {table}: {count}")

    if not arguments.confirm:
        print("\nNo data was changed.")
        print("Run again with --confirm to back up and clear these records.")
        return 0

    backup_path, counts = clear_data(database_path)
    print(f"\nBackup created: {backup_path}")
    print("Data cleared. Remaining records:")
    for table, count in counts.items():
        print(f"  {table}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
