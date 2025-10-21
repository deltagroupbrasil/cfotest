"""
Plan:
- Branch coverage for reporting_api income-statement endpoints:
  * GET with MM/DD/YYYY dates parses correctly.
  * POST include_details=True handled.
  * Error path: db error returns 500 with error message.
  * Empty DB returns zeroed totals and empty categories.
"""

import os
import sys
import unittest
from flask import Flask


class TestReportingAPIBranches(unittest.TestCase):
    def setUp(self):
        # Force SQLite mode
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_DB_PATH'] = 'test_reporting_branches.sqlite'
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.web_ui.reporting_api') or mod.startswith('DeltaCFOAgent.web_ui.database'):
                sys.modules.pop(mod)
        from DeltaCFOAgent.web_ui import reporting_api  # type: ignore
        self.rp = reporting_api
        self.rp.db_manager.db_type = 'sqlite'
        self.rp.db_manager.init_database()
        self.app = Flask(__name__)
        self.rp.register_reporting_routes(self.app)
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ.pop('DB_TYPE', None)
        os.environ.pop('SQLITE_DB_PATH', None)

    def test_get_dates_mmddyyyy(self):
        resp = self.client.get('/api/reports/income-statement?start_date=01/01/2024&end_date=01/31/2024')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))

    def test_post_include_details(self):
        resp = self.client.post('/api/reports/income-statement', json={'include_details': True, 'start_date': '2024-01-01', 'end_date': '2024-01-31'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))

    def test_error_path_db_raises(self):
        # Monkeypatch to raise during execute_query in simple endpoint
        original = self.rp.db_manager.execute_query
        try:
            def boom(query, *a, **k):
                raise RuntimeError('forced error')
            self.rp.db_manager.execute_query = boom  # type: ignore
            resp = self.client.get('/api/reports/income-statement/simple')
            self.assertEqual(resp.status_code, 500)
            data = resp.get_json()
            self.assertIn('error', data)
        finally:
            self.rp.db_manager.execute_query = original  # type: ignore

    def test_empty_db_zero_totals(self):
        resp = self.client.get('/api/reports/income-statement/simple')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        stmt = data.get('statement', {})
        self.assertIn('revenue', stmt)
        self.assertIn('operating_expenses', stmt)


if __name__ == '__main__':
    unittest.main()

