"""Verified SQLite backup from the running Compose API; run on the Linux host."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time


EXPORT = """
import os, sqlite3, sys, tempfile, shutil
fd, name = tempfile.mkstemp(suffix='.db')
os.close(fd)
try:
    source = sqlite3.connect('file:/data/expenses.db?mode=ro', uri=True)
    target = sqlite3.connect(name)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    with open(name, 'rb') as stream:
        shutil.copyfileobj(stream, sys.stdout.buffer)
finally:
    os.unlink(name)
"""


def backup(project, destination, retention_days=14):
    if retention_days < 1:
        raise ValueError('Retention must be positive')
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Preserve the destination owner's access when the system service runs as root.
    owner = destination.stat()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    final = destination / f'expenses-{timestamp}.db'
    fd, temporary = tempfile.mkstemp(prefix='.backup-', suffix='.tmp', dir=destination)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as output:
            subprocess.run(
                ['docker', 'compose', '--env-file', 'backend/.env.docker',
                 'exec', '-T', 'viaje-claro-api', 'python', '-c', EXPORT],
                cwd=project, stdout=output, check=True, timeout=600,
            )
            output.flush()
            os.fsync(output.fileno())
        connection = sqlite3.connect(temporary.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise RuntimeError('Backup integrity check failed')
            if connection.execute('PRAGMA foreign_key_check').fetchone():
                raise RuntimeError('Backup foreign key check failed')
            if not connection.execute('SELECT version_num FROM alembic_version').fetchone():
                raise RuntimeError('Missing migration version')
        finally:
            connection.close()
        temporary.chmod(0o600)
        if hasattr(os, 'chown'):
            os.chown(temporary, owner.st_uid, owner.st_gid)
        temporary.replace(final)
        # Expire only our dated backups, and only after a verified new backup exists.
        cutoff = time.time() - retention_days * 86400
        for path in destination.iterdir():
            if (path != final and not path.is_symlink() and path.is_file()
                    and re.fullmatch(r'expenses-\d{8}T\d{6}(?:\d{6})?Z\.db', path.name)
                    and path.stat().st_mtime < cutoff):
                path.unlink()
        print(f'Verified backup: {final}', flush=True)
        return final
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--retention-days', type=int, default=14)
    args = parser.parse_args()
    backup(Path(__file__).resolve().parents[1], args.destination, args.retention_days)
