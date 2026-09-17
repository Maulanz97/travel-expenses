import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from backup_sqlite import backup


class BackupTests(unittest.TestCase):
    def test_verified_backup_and_scoped_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.db'
            db = sqlite3.connect(source)
            db.executescript("CREATE TABLE alembic_version(version_num TEXT); INSERT INTO alembic_version VALUES ('test');")
            db.close()
            destination = root / 'backups'
            destination.mkdir()
            expired = destination / 'expenses-20200101T030000Z.db'
            unrelated = destination / 'important.db'
            for path in (expired, unrelated):
                path.write_bytes(b'keep unless dated')
                os.utime(path, (time.time() - 20 * 86400,) * 2)

            def export(*args, **kwargs):
                kwargs['stdout'].write(source.read_bytes())

            with patch('backup_sqlite.subprocess.run', side_effect=export):
                result = backup(root, destination)
            self.assertEqual(result.read_bytes(), source.read_bytes())
            self.assertFalse(expired.exists())
            self.assertTrue(unrelated.exists())
            self.assertEqual(list(destination.glob('.backup-*')), [])

    def test_failed_export_or_corrupt_copy_preserves_old_backups(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                old = root / 'expenses-20200101T030000Z.db'
                old.write_bytes(b'previous backup')
                os.utime(old, (time.time() - 20 * 86400,) * 2)

                def export(*args, **kwargs):
                    kwargs['stdout'].write(b'invalid database')
                    if not corrupt:
                        raise subprocess.CalledProcessError(1, 'docker')

                with patch('backup_sqlite.subprocess.run', side_effect=export):
                    with self.assertRaises((subprocess.CalledProcessError, sqlite3.DatabaseError)):
                        backup(root, root)
                self.assertEqual(list(root.iterdir()), [old])


if __name__ == '__main__':
    unittest.main()
