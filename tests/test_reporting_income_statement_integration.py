"""
Plan:
- Initialize SQLite DB schema and seed transactions for revenue and expenses.
- Call /api/reports/income-statement/simple and validate totals and categories.
- Edge cases: missing categories fall to defaults; date filters applied.
"""

import os
import sys
import tempfile
import unittest
from datetime import date
from flask import Flask


class TestIncomeStatementIntegration(unittest.TestCase):
    def setUp(self):
        # temp sqlite db
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test_finance.sqlite')
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_DB_PATH'] = self.db_path

        # Fresh import
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.web_ui.database') or mod.startswith('DeltaCFOAgent.web_ui.reporting_api'):
                sys.modules.pop(mod)

        from DeltaCFOAgent.web_ui import reporting_api  # type: ignore
        self.reporting_api = reporting_api
        # Ensure schema
        reporting_api.db_manager.db_type = 'sqlite'
        reporting_api.db_manager.init_database()

        # Seed transactions (two revenue categories, one expense)
        rows = [
            # revenue
            {
                'transaction_id': 'r1',
                'date': '2024-01-05',
                'description': 'Sale A',
                'amount': 100.0,
                'currency': 'USD',
                'usd_equivalent': 100.0,
                'accounting_category': 'Sales',
                'classified_entity': 'EntityA'
            },
            {
                'transaction_id': 'r2',
                'date': '2024-01-06',
                'description': 'Sale B',
                'amount': 50.0,
                'currency': 'USD',
                'usd_equivalent': 50.0,
                'accounting_category': None,
                'classified_entity': 'OtherRevenue'
            },
            # expense
            {
                'transaction_id': 'e1',
                'date': '2024-01-07',
                'description': 'Office Supplies',
                'amount': -30.0,
                'currency': 'USD',
                'usd_equivalent': -30.0,
                'accounting_category': 'General & Administrative',
                'classified_entity': 'EntityB'
            },
        ]

        ins = """
            INSERT OR REPLACE INTO transactions (
              transaction_id, date, description, amount, currency, usd_equivalent,
              accounting_category, classified_entity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [(
            r['transaction_id'], r['date'], r['description'], r['amount'], r['currency'], r['usd_equivalent'],
            r['accounting_category'], r['classified_entity']
        ) for r in rows]
        reporting_api.db_manager.execute_many(ins, params)

        # Build isolated Flask app and register routes
        self.app = Flask(__name__)
        reporting_api.register_reporting_routes(self.app)
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ.pop('DB_TYPE', None)
        os.environ.pop('SQLITE_DB_PATH', None)
        self.tmpdir.cleanup()

    def test_income_statement_simple_integration(self):
        # Query across seeded date range
        resp = self.client.get('/api/reports/income-statement/simple')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        stmt = data['statement']

        # Verify totals at least reflect seeded data (>=150 revenue)
        self.assertGreaterEqual(stmt['revenue']['total'], 150.0)
        self.assertGreaterEqual(len(stmt['revenue']['categories']), 1)
        # Operating expenses is positive number in response
        self.assertGreaterEqual(stmt['operating_expenses']['total'], 30.0)
        # Net income field present
        self.assertIn('net_income', stmt)


if __name__ == '__main__':
    unittest.main()
