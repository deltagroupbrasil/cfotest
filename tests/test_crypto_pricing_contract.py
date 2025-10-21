"""
Plan:
- Contract test for Binance klines fetch: ensure correct URL/params and batch insert operations.
- Verify stablecoins path inserts fixed price records via execute_batch_operation.
"""

import os
import sys
import types
import unittest
from datetime import datetime


class TestCryptoPricingContract(unittest.TestCase):
    def setUp(self):
        # Force SQLite db path
        self.tmpdir = os.path.abspath('tmp_test_pricing')
        os.makedirs(self.tmpdir, exist_ok=True)
        self.db_path = os.path.join(self.tmpdir, 'pricing.sqlite')
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_DB_PATH'] = self.db_path

        # Ensure fresh import of modules
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.crypto_pricing') or mod.startswith('DeltaCFOAgent.web_ui.database'):
                sys.modules.pop(mod)

        # Stub requests with a local module to capture call
        req_mod = types.ModuleType('requests')
        captured = {'called': False, 'url': None, 'params': None}

        class Resp:
            def __init__(self, data):
                self._data = data
            def raise_for_status(self):
                return None
            def json(self):
                return self._data

        def fake_get(url, params=None, timeout=30):
            captured['called'] = True
            captured['url'] = url
            captured['params'] = params
            # Produce two klines (timestamp, open, high, low, close,...)
            day1 = int(datetime(2024, 1, 1).timestamp() * 1000)
            day2 = int(datetime(2024, 1, 2).timestamp() * 1000)
            data = [
                [day1, '100', '110', '90', '105', '1'],
                [day2, '105', '115', '95', '110', '1'],
            ]
            return Resp(data)

        req_mod.get = fake_get
        sys.modules['requests'] = req_mod

        from DeltaCFOAgent.crypto_pricing import CryptoPricingDB  # type: ignore
        self.pricing = CryptoPricingDB()

        # Monkeypatch db to capture batch operations
        self.captured_ops = []
        def fake_batch(ops, batch_size=100):
            self.captured_ops.extend(ops)
            return {'successful_batches': 1, 'failed_batches': 0, 'total_rows_affected': len(ops), 'errors': []}

        self.pricing.db.execute_batch_operation = fake_batch  # type: ignore
        self._captured = captured

    def tearDown(self):
        os.environ.pop('DB_TYPE', None)
        os.environ.pop('SQLITE_DB_PATH', None)

    def test_fetch_binance_btc_inserts_prices(self):
        self.pricing.fetch_historic_prices_binance('BTC', start_date='2024-01-01', end_date='2024-01-02')
        self.assertTrue(self._captured['called'])
        self.assertIn('binance.com', self._captured['url'])
        self.assertGreaterEqual(len(self.captured_ops), 2)
        # Ensure query structure contains insert/replace for sqlite
        self.assertTrue(any('INSERT' in op['query'].upper() for op in self.captured_ops))

    def test_stablecoin_inserts_fixed_prices(self):
        # Reset ops
        self.captured_ops.clear()
        self.pricing.insert_stable_prices('USDC', '2024-01-01', '2024-01-03', price=1.0)
        self.assertEqual(len(self.captured_ops), 3)
        self.assertTrue(all(op['params'][2] == 1.0 for op in self.captured_ops))


if __name__ == '__main__':
    unittest.main()

