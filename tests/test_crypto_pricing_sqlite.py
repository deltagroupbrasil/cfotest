import os
import sys
import io
import tempfile
import types
import unittest
from datetime import datetime, timedelta


def _install_psycopg2_stub():
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

def _install_dotenv_requests_pandas_stubs():
    # dotenv
    dotenv = types.SimpleNamespace()
    def load_dotenv(*args, **kwargs):
        return False
    dotenv.load_dotenv = load_dotenv
    sys.modules.setdefault('dotenv', dotenv)
    # requests (not used in these tests)
    requests = types.SimpleNamespace()
    sys.modules.setdefault('requests', requests)
    # pandas (not used in these tests directly)
    pandas = types.SimpleNamespace()
    sys.modules.setdefault('pandas', pandas)


class TestCryptoPricingSQLite(unittest.TestCase):
    def setUp(self):
        _install_psycopg2_stub()
        _install_dotenv_requests_pandas_stubs()
        # Force SQLite mode and temp db
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "pricing.sqlite")
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_DB_PATH'] = self.db_path

        # Ensure fresh imports honoring env
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.web_ui.database') or mod.startswith('DeltaCFOAgent.crypto_pricing'):
                sys.modules.pop(mod)
        # Also clear any prior top-level 'database' module imported by crypto_pricing
        sys.modules.pop('database', None)

        # Import after env is set
        # Avoid Windows console encoding issues with emojis in print
        self._stdout = sys.stdout
        sys.stdout = io.StringIO()

        from DeltaCFOAgent.crypto_pricing import CryptoPricingDB  # type: ignore
        self.CryptoPricingDB = CryptoPricingDB
        self.pricing = CryptoPricingDB()

        # Ensure schema exists
        self.pricing.db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS crypto_historic_prices (
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price_usd REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, symbol)
            );
            """
        )

    def tearDown(self):
        # Restore stdout
        sys.stdout = self._stdout
        try:
            self.tmpdir.cleanup()
        except PermissionError:
            # Ignore Windows file locking races on temp cleanup
            pass
        os.environ.pop('DB_TYPE', None)
        os.environ.pop('SQLITE_DB_PATH', None)

    def test_insert_stable_and_get_price(self):
        start = '2024-01-01'
        end = '2024-01-03'
        self.pricing.insert_stable_prices('USDC', start, end, price=1.0)

        p = self.pricing.get_price_on_date('USDC', '2024-01-02')
        self.assertEqual(p, 1.0)

    def test_get_price_with_fallback(self):
        # Insert BTC price on a specific day
        day = datetime(2024, 5, 10)
        q = {
            'query': "INSERT OR REPLACE INTO crypto_historic_prices (date, symbol, price_usd, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            'params': (day.strftime('%Y-%m-%d'), 'BTC', 67890.0)
        }
        res = self.pricing.db.execute_batch_operation([q], batch_size=10)
        self.assertEqual(res['failed_batches'], 0)

        # Request two days later -> fallback within 7 days should find it
        lookup_day = (day + timedelta(days=2)).strftime('%Y-%m-%d')
        p = self.pricing.get_price_on_date('BTC', lookup_day)
        self.assertEqual(p, 67890.0)


if __name__ == "__main__":
    unittest.main()
