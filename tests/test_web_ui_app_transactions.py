import unittest
import pandas as pd
import sys


class TestWebUIAppTransactions(unittest.TestCase):
    def setUp(self):
        # Fresh import of module to avoid prior monkeypatches
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.web_ui.app'):
                sys.modules.pop(mod)

        from DeltaCFOAgent.web_ui import app as appmod  # type: ignore
        self.appmod = appmod

        # Build a small DataFrame fixture
        self.df = pd.DataFrame([
            {
                'Date': '2024-01-01', 'Amount': 100.0, 'classified_entity': 'EntityA',
                'source_file': 'file1.csv', 'Description': 'Revenue from service',
                'confidence': 0.9, 'keywords_action_type': 'sale', 'keywords_platform': 'web'
            },
            {
                'Date': '2024-01-02', 'Amount': -50.0, 'classified_entity': 'EntityB',
                'source_file': 'file2.csv', 'Description': 'Office supplies',
                'confidence': 0.7, 'keywords_action_type': 'expense', 'keywords_platform': 'store'
            },
            {
                'Date': '2024-01-03', 'Amount': 25.0, 'classified_entity': 'EntityA',
                'source_file': 'file1.csv', 'Description': 'Other income',
                'confidence': None, 'keywords_action_type': 'other', 'keywords_platform': 'web'
            }
        ])

        # Monkeypatch loader
        def fake_load_master_transactions():
            return self.df.copy()

        self.appmod.load_master_transactions = fake_load_master_transactions  # type: ignore
        self.client = self.appmod.app.test_client()

    def test_no_filters_returns_all(self):
        resp = self.client.get('/api/transactions')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data), 3)

    def test_entity_and_type_filters(self):
        # Filter by entity
        resp = self.client.get('/api/transactions?entity=EntityA')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(all(d.get('classified_entity') == 'EntityA' for d in data))

        # Revenue filter (> 0)
        resp = self.client.get('/api/transactions?transaction_type=Revenue')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(all((d.get('Amount') or 0) > 0 for d in data))

        # Expense filter (< 0)
        resp = self.client.get('/api/transactions?transaction_type=Expense')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(all((d.get('Amount') or 0) < 0 for d in data))

    def test_needs_review_and_amount_filters(self):
        # needs_review=true selects confidence < 0.8 or NaN
        resp = self.client.get('/api/transactions?needs_review=true')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Row 2 (0.7) and row 3 (NaN) match => 2
        self.assertEqual(len(data), 2)

        # min/max by absolute value
        resp = self.client.get('/api/transactions?min_amount=40')
        data = resp.get_json()
        # 100 and -50 pass (abs >= 40)
        self.assertEqual(len(data), 2)

        resp = self.client.get('/api/transactions?max_amount=30')
        data = resp.get_json()
        # 25 passes (abs <= 30)
        self.assertEqual(len(data), 1)

    def test_keyword_and_source_filters(self):
        # keyword in Description/keywords_* columns
        resp = self.client.get('/api/transactions?keyword=office')
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertIn('Office supplies', data[0].get('Description', ''))

        # source_file filter
        resp = self.client.get('/api/transactions?source_file=file1.csv')
        data = resp.get_json()
        self.assertTrue(all(d.get('source_file') == 'file1.csv' for d in data))


if __name__ == '__main__':
    unittest.main()

