import os
import sys
import tempfile
import types
import unittest


def _install_psycopg2_stub():
    # Minimal psycopg2 stub so module import succeeds without real dependency
    psycopg2 = types.SimpleNamespace()
    class OperationalError(Exception):
        pass
    psycopg2.OperationalError = OperationalError
    psycopg2.extras = types.SimpleNamespace(RealDictCursor=object)
    class _DummyPool:
        def __init__(self, *args, **kwargs):
            self._pool = []
            self._used = []
        def closeall(self):
            pass
        def getconn(self):
            return None
        def putconn(self, conn):
            pass
    psycopg2.pool = types.SimpleNamespace(ThreadedConnectionPool=_DummyPool)
    def _connect(**kwargs):
        raise OperationalError("psycopg2 stub: no PostgreSQL available")
    psycopg2.connect = _connect
    sys.modules.setdefault('psycopg2', psycopg2)
    sys.modules.setdefault('psycopg2.extras', psycopg2.extras)
    sys.modules.setdefault('psycopg2.pool', psycopg2.pool)

def _install_dotenv_stub():
    import types as _types
    dotenv = _types.SimpleNamespace()
    def load_dotenv(*args, **kwargs):
        return False
    dotenv.load_dotenv = load_dotenv
    sys.modules.setdefault('dotenv', dotenv)


class TestWebUIDatabaseSQLite(unittest.TestCase):
    def setUp(self):
        _install_psycopg2_stub()
        _install_dotenv_stub()
        # Force SQLite mode with a temp database path
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "webui_test.sqlite")
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_DB_PATH'] = self.db_path

        # Re-import the module fresh so it picks up env vars and stub
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.web_ui.database'):
                sys.modules.pop(mod)

        from DeltaCFOAgent.web_ui import database as dbmod  # type: ignore
        self.dbmod = dbmod
        self.manager = dbmod.DatabaseManager()

        # Create a sample table
        with self.manager.get_connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER)"
            )
            conn.commit()

    def tearDown(self):
        try:
            self.tmpdir.cleanup()
        except PermissionError:
            pass
        os.environ.pop('DB_TYPE', None)
        os.environ.pop('SQLITE_DB_PATH', None)

    def test_execute_query_fetch_one_and_all(self):
        # Insert using execute_query (no fetch -> returns rowcount)
        rc = self.manager.execute_query(
            "INSERT INTO t (name, qty) VALUES (?, ?)", ("alpha", 10)
        )
        self.assertEqual(rc, 1)

        one = self.manager.execute_query(
            "SELECT name, qty FROM t WHERE name=?", ("alpha",), fetch_one=True
        )
        self.assertIsNotNone(one)

        all_rows = self.manager.execute_query(
            "SELECT name, qty FROM t", fetch_all=True
        )
        self.assertEqual(len(all_rows), 1)

    def test_execute_many(self):
        rows = self.manager.execute_many(
            "INSERT INTO t (name, qty) VALUES (?, ?)",
            [("a", 1), ("b", 2), ("c", 3)],
        )
        self.assertEqual(rows, 3)

    def test_get_transaction_commit(self):
        with self.manager.get_transaction() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO t (name, qty) VALUES (?, ?)", ("tx", 5))
            cur.close()
        # After context, committed
        count = self.manager.execute_query("SELECT COUNT(*) FROM t", fetch_one=True)
        # sqlite3.Row: index 0
        self.assertIn(count[0], (1,))

    def test_get_transaction_rollback(self):
        with self.assertRaises(Exception):
            with self.manager.get_transaction() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO t (name, qty) VALUES (?, ?)", ("will_rollback", 7))
                # Cause error to trigger rollback
                cur.execute("INSERT INTO non_existing(col) VALUES (1)")
                cur.close()

        # Ensure previous insert did not persist
        rows = self.manager.execute_query(
            "SELECT COUNT(*) FROM t WHERE name=?", ("will_rollback",), fetch_one=True
        )
        self.assertEqual(rows[0], 0)

    def test_execute_batch_operation(self):
        ops = []
        for n, q in [("x", 1), ("y", 2), ("z", 3)]:
            ops.append({"query": "INSERT INTO t (name, qty) VALUES (?, ?)", "params": (n, q)})
        res = self.manager.execute_batch_operation(ops, batch_size=2)
        self.assertEqual(res['total_operations'], 3)
        self.assertEqual(res['failed_batches'], 0)
        self.assertGreaterEqual(res['successful_batches'], 1)
        self.assertEqual(res['total_rows_affected'], 3)

    def test_execute_with_retry_success_after_fail(self):
        # Monkeypatch execute_query to fail once with OperationalError, then succeed
        calls = {"n": 0}
        original = self.manager.execute_query

        def fake_exec(query, params=None, fetch_one=False, fetch_all=False):
            calls["n"] += 1
            if calls["n"] == 1:
                # Raise the stubbed OperationalError
                from psycopg2 import OperationalError  # type: ignore
                raise OperationalError("transient")
            # On retry, execute real query
            if "SELECT 1" in query:
                with self.manager.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    row = cur.fetchone()
                    cur.close()
                    conn.commit()
                    return row
            return original(query, params, fetch_one, fetch_all)

        self.manager.execute_query = fake_exec  # type: ignore
        try:
            row = self.manager.execute_with_retry("SELECT 1", fetch_one=True)
            self.assertIsNotNone(row)
            # Row[0] should be 1
            self.assertEqual(row[0], 1)
            self.assertEqual(calls["n"], 2)
        finally:
            self.manager.execute_query = original  # type: ignore

    def test_health_check(self):
        status = self.manager.health_check()
        self.assertEqual(status.get('db_type'), 'sqlite')
        self.assertIn(status.get('status'), ('healthy', 'unhealthy'))
        self.assertIsNone(status.get('error')) if status.get('status') == 'healthy' else None


if __name__ == "__main__":
    unittest.main()
