import os
import tempfile
import unittest
from pathlib import Path

from DeltaCFOAgent.database_utils import (
    DatabaseManager,
    get_database_manager,
    fix_database_locks,
)


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for database files
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_db.sqlite")
        # Ensure the file is created by touching it via a connection
        self.manager = DatabaseManager(self.db_path)
        with self.manager.get_connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER)"
            )
            conn.commit()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_execute_update_and_query(self):
        # Insert a row
        rows = self.manager.execute_update(
            "INSERT INTO items (name, qty) VALUES (?, ?)", ("widget", 3)
        )
        self.assertEqual(rows, 1)

        # Query it back
        results = self.manager.execute_query(
            "SELECT name, qty FROM items WHERE name = ?", ("widget",)
        )
        self.assertEqual(len(results), 1)
        row = results[0]
        # sqlite3.Row supports index/key access
        self.assertEqual(row[0], "widget")
        self.assertEqual(row[1], 3)

    def test_execute_batch_transaction(self):
        queries = [
            ("INSERT INTO items (name, qty) VALUES (?, ?)", ("a", 1)),
            ("INSERT INTO items (name, qty) VALUES (?, ?)", ("b", 2)),
            ("INSERT INTO items (name, qty) VALUES (?, ?)", ("c", 3)),
        ]
        ok = self.manager.execute_batch(queries)
        self.assertTrue(ok)

        results = self.manager.execute_query("SELECT COUNT(*) FROM items")
        self.assertEqual(results[0][0], 3)

    def test_check_integrity_ok(self):
        self.assertTrue(self.manager.check_integrity())

    def test_vacuum_database(self):
        # Should not raise
        self.manager.vacuum_database()
        # Simple sanity: still can query
        self.assertTrue(self.manager.check_integrity())

    def test_fix_database_locks_removes_lock_files(self):
        # Create dummy lock-related files to simulate leftover lock artifacts
        wal = Path(self.db_path + "-wal")
        shm = Path(self.db_path + "-shm")
        journal = Path(self.db_path + "-journal")
        for p in (wal, shm, journal):
            p.write_text("")
            self.assertTrue(p.exists())

        # Call the lock fix utility
        ok = fix_database_locks(self.db_path)
        self.assertTrue(ok)

        # Ensure files were removed
        for p in (wal, shm, journal):
            self.assertFalse(p.exists())

    def test_get_database_manager_singleton(self):
        mgr1 = get_database_manager(self.db_path)
        mgr2 = get_database_manager(self.db_path)
        self.assertIs(mgr1, mgr2)

        # Different path -> different instance
        other_path = os.path.join(self.tmpdir.name, "other.sqlite")
        mgr3 = get_database_manager(other_path)
        self.assertIsNot(mgr1, mgr3)

    def test_execute_update_invalid_query_raises(self):
        with self.assertRaises(Exception):
            self.manager.execute_update("INSERT INTO no_table(col) VALUES (1)")


if __name__ == "__main__":
    unittest.main()

