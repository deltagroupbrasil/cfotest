import sys
import types
import unittest
from datetime import datetime, timedelta


class TestRobustRevenueMatcherHelpers(unittest.TestCase):
    def setUp(self):
        # Stub anthropic
        sys.modules['anthropic'] = types.SimpleNamespace(Anthropic=lambda *a, **k: object())
        # Stub db_manager with minimal interface used by helpers
        # Patchable db_manager stub; we overwrite execute_with_retry in specific tests
        fake_db_manager = types.SimpleNamespace(
            db_type='sqlite',
            execute_with_retry=lambda *a, **k: [],
            execute_query=lambda *a, **k: 1,
            health_check=lambda: {'status': 'healthy'}
        )
        # Inject stubbed database into module namespace via import
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.web_ui.robust_revenue_matcher'):
                sys.modules.pop(mod)
        # Stub learning_system module expected by robust_revenue_matcher
        learn_mod = types.ModuleType('learning_system')
        learn_mod.apply_learning_to_scores = lambda *a, **k: None
        learn_mod.record_match_feedback = lambda *a, **k: None
        sys.modules['learning_system'] = learn_mod

        from DeltaCFOAgent.web_ui import robust_revenue_matcher as rrm  # type: ignore
        # Monkeypatch module-level db_manager used inside class methods
        rrm.db_manager = fake_db_manager  # type: ignore
        self.rrm = rrm
        self.matcher = rrm.RobustRevenueInvoiceMatcher()

    def test_chunk_list(self):
        data = list(range(23))
        chunks = list(self.matcher._chunk_list(data, 5))
        self.assertEqual(len(chunks), 5)  # 5,5,5,5,3
        self.assertEqual(chunks[0], [0,1,2,3,4])
        self.assertEqual(chunks[-1], [20,21,22])

    def test_build_error_result(self):
        stats = self.rrm.MatchingStats(
            total_invoices_processed=10,
            total_matches_found=2,
            high_confidence_matches=1,
            medium_confidence_matches=1,
            auto_applied_matches=0,
            pending_review_matches=2,
            processing_time_seconds=0.0,
            database_operations=0,
            errors_count=1,
            batch_stats={'batch_1': {'status': 'failed'}}
        )
        start = datetime.now() - timedelta(seconds=1)
        res = self.matcher._build_error_result(stats, 'Boom', start)
        self.assertFalse(res['success'])
        self.assertIn('Boom', res['error'])
        self.assertIn('stats', res)

    def test_build_result_dict_enrich_empty(self):
        stats = self.rrm.MatchingStats(
            total_invoices_processed=0,
            total_matches_found=0,
            high_confidence_matches=0,
            medium_confidence_matches=0,
            auto_applied_matches=0,
            pending_review_matches=0,
            processing_time_seconds=0.0,
            database_operations=0,
            errors_count=0,
            batch_stats={}
        )
        start = datetime.now() - timedelta(milliseconds=100)
        res = self.matcher._build_result_dict(stats, [], start)
        self.assertTrue(res['success'])
        self.assertIsInstance(res.get('matches'), list)

    def test_generate_match_explanation_high_confidence(self):
        # Create scores that lead to high final score
        criteria = {
            'amount': 0.95,
            'date': 0.9,
            'vendor': 0.85,
            'entity': 0.8,
            'pattern': 0.9,
        }
        invoice = {
            'total_amount': 100.0,
            'vendor_name': 'Acme Corp',
            'invoice_number': 'INV-999'
        }
        transaction = {
            'amount': 100.0,
            'description': 'Paid ACME CORP INV-999'
        }

        text = self.matcher._generate_match_explanation(criteria, invoice, transaction)
        self.assertIsInstance(text, str)
        self.assertNotEqual(text.strip(), '')
        # Look for a marker of high confidence (string contains 'ALTA')
        self.assertIn('ALTA', text)

    def test_enrich_matches_with_details(self):
        # Monkeypatch execute_with_retry to return rows based on query text
        def fake_exec(query, params=None, fetch_all=False, fetch_one=False):
            q = (query or '').lower()
            if 'from invoices' in q:
                return [
                    {'id': 'inv-1', 'invoice_number': 'INV-1', 'date': '2024-01-01', 'customer_name': 'Cust', 'total_amount': 100.0, 'currency': 'USD', 'business_unit': 'Delta LLC'}
                ]
            if 'from transactions' in q:
                return [
                    {'transaction_id': 'tx-1', 'date': '2024-01-02', 'description': 'Desc', 'amount': 100.0, 'currency': 'USD', 'classified_entity': 'delta llc'}
                ]
            return []

        self.rrm.db_manager.execute_with_retry = fake_exec  # type: ignore

        match = self.rrm.MatchResult(
            invoice_id='inv-1',
            transaction_id='tx-1',
            score=0.9,
            match_type='COMBINED',
            criteria_scores={'amount': 0.95, 'date': 0.9, 'vendor': 0.9, 'entity': 0.8, 'pattern': 0.9},
            confidence_level='HIGH',
            explanation='ok',
            auto_match=True,
        )

        enriched = self.matcher._enrich_matches_with_details([match])
        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0]['invoice']['invoice_number'], 'INV-1')
        self.assertEqual(enriched[0]['transaction']['description'], 'Desc')


if __name__ == '__main__':
    unittest.main()
