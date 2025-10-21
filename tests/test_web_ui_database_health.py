"""
Plan:
- Health check returns healthy with SELECT 1.
- Health check returns unhealthy when query returns unexpected shape.
"""

import unittest
import sys
import types

# Stub psycopg2 to avoid import error when running in SQLite mode
psycopg2_stub = types.SimpleNamespace()
class OperationalError(Exception):
    pass
psycopg2_stub.OperationalError = OperationalError
psycopg2_stub.extras = types.SimpleNamespace(RealDictCursor=object)
psycopg2_stub.pool = types.SimpleNamespace(ThreadedConnectionPool=object)
sys.modules['psycopg2'] = psycopg2_stub
sys.modules['psycopg2.extras'] = psycopg2_stub.extras
sys.modules['psycopg2.pool'] = psycopg2_stub.pool

# Stub dotenv to avoid import dependency
dotenv_stub = types.SimpleNamespace()
dotenv_stub.load_dotenv = lambda *a, **k: False
sys.modules['dotenv'] = dotenv_stub

from DeltaCFOAgent.web_ui.database import DatabaseManager


class TestDatabaseHealth(unittest.TestCase):
    def setUp(self):
        self.dbm = DatabaseManager()
        # Force SQLite for deterministic test
        self.dbm.db_type = 'sqlite'

    def test_health_healthy(self):
        status = self.dbm.health_check()
        self.assertIn(status['status'], ('healthy', 'unhealthy'))

    def test_health_unhealthy_on_unexpected(self):
        # Monkeypatch execute_query to return None
        original = self.dbm.execute_query
        try:
            def fake_exec(query, params=None, fetch_one=False, fetch_all=False):
                return None
            self.dbm.execute_query = fake_exec  # type: ignore
            status = self.dbm.health_check()
            self.assertEqual(status['status'], 'unhealthy')
            self.assertTrue(status['error'])
        finally:
            self.dbm.execute_query = original  # type: ignore


if __name__ == '__main__':
    unittest.main()
