import sys
import types
import unittest
try:
    from flask import Flask
except ImportError:  # pragma: no cover
    Flask = None


@unittest.skipIf(Flask is None, "Flask not installed; skipping web_ui app tests")
class TestWebUIAppStats(unittest.TestCase):
    def setUp(self):
        # Provide a minimal pandas stub for import
        pd = types.SimpleNamespace()
        def isna(x):
            return x is None
        pd.isna = isna
        sys.modules.setdefault('pandas', pd)

        # Fresh import of the module
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.web_ui.app'):
                sys.modules.pop(mod)

        from DeltaCFOAgent.web_ui import app as appmod  # type: ignore
        self.appmod = appmod

        # Monkeypatch helpers
        def fake_load_master_transactions():
            return object()  # placeholder; get_dashboard_stats ignores its content in this test

        def fake_get_dashboard_stats(df):
            return {
                'total_transactions': 2,
                'total_revenue': 100.0,
                'total_expenses': 40.0,
                'needs_review': 1,
                'date_range': {'min': '2024-01-01', 'max': '2024-01-31'},
                'entities': [('A', 1), ('B', 1)],
                'source_files': [('file1.csv', 1), ('file2.csv', 1)],
            }

        appmod.load_master_transactions = fake_load_master_transactions  # type: ignore
        appmod.get_dashboard_stats = fake_get_dashboard_stats  # type: ignore

        self.client = appmod.app.test_client()

    def test_api_stats(self):
        resp = self.client.get('/api/stats')
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertEqual(payload['total_transactions'], 2)
        self.assertEqual(payload['total_revenue'], 100.0)
        self.assertEqual(payload['total_expenses'], 40.0)


if __name__ == '__main__':
    unittest.main()
