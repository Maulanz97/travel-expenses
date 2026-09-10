"""Back up the local SQLite database before applying additive migrations."""
from datetime import datetime
from pathlib import Path
import sqlite3
from alembic import command
from alembic.config import Config

root = Path(__file__).resolve().parents[1]
database = root / "expenses.db"
if database.exists():
    backup = root / f"expenses-{datetime.now():%Y%m%d-%H%M%S}.db.bak"
    with sqlite3.connect(database) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
    print(f"Backup: {backup}")
config = Config(str(root / "alembic.ini"))
config.set_main_option("script_location", str(root / "alembic"))
config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
command.upgrade(config, "head")
