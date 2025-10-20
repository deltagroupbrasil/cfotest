import os
import sys
import types
import unittest


class TestSmartMatchingCriteria(unittest.TestCase):
    def setUp(self):
        # Ensure anthropic absence doesn't break import by stubbing
        import types
        fake_anthropic = types.SimpleNamespace(Anthropic=lambda *args, **kwargs: object())
        sys.modules['anthropic'] = fake_anthropic
        from DeltaCFOAgent.web_ui.smart_matching_criteria import SmartMatchingValidator
        self.validator = SmartMatchingValidator()

        self.invoice_base = {
            'currency': 'USD',
            'total_amount': 100.0,
            'date': '2024-01-10',
            'due_date': '2024-01-15',
            'vendor_name': 'Acme Corp',
            'business_unit': 'Delta LLC',
            'invoice_number': 'INV-12345'
        }

        self.tx_base = {
            'amount': 100.0,
            'date': '2024-01-15',
            'description': 'Payment to Acme Corp INV-12345',
            'classified_entity': 'delta llc'
        }

    def test_amount_score_exact_or_near(self):
        score, expl = self.validator._calculate_smart_amount_score(self.invoice_base, self.tx_base)
        self.assertGreaterEqual(score, 0.9)

        tx = dict(self.tx_base, amount=95.0)
        score2, _ = self.validator._calculate_smart_amount_score(self.invoice_base, tx)
        self.assertGreater(score2, 0.2)

    def test_amount_threshold_boundaries(self):
        # 2% boundary (strict)
        tx_98 = dict(self.tx_base, amount=98.0)  # 2% below 100
        s98, _ = self.validator._calculate_smart_amount_score(self.invoice_base, tx_98)
        self.assertGreaterEqual(s98, 0.9)

        # 5% boundary (loose)
        tx_95 = dict(self.tx_base, amount=95.0)
        s95, _ = self.validator._calculate_smart_amount_score(self.invoice_base, tx_95)
        self.assertGreaterEqual(s95, 0.50)

        # 10% boundary
        tx_90 = dict(self.tx_base, amount=90.0)
        s90, _ = self.validator._calculate_smart_amount_score(self.invoice_base, tx_90)
        self.assertEqual(s90, 0.50)

        # 15% boundary
        tx_85 = dict(self.tx_base, amount=85.0)
        s85, _ = self.validator._calculate_smart_amount_score(self.invoice_base, tx_85)
        self.assertEqual(s85, 0.20)

    def test_amount_score_large_difference(self):
        tx = dict(self.tx_base, amount=50.0)
        score, _ = self.validator._calculate_smart_amount_score(self.invoice_base, tx)
        self.assertEqual(score, 0.0)

    def test_date_score_buckets(self):
        inv = dict(self.invoice_base)
        tx_same = dict(self.tx_base, date='2024-01-15')  # equals due_date
        s_exact, _ = self.validator._calculate_smart_date_score(inv, tx_same)
        self.assertGreaterEqual(s_exact, 0.95)

        tx_3 = dict(self.tx_base, date='2024-01-18')
        s_3, _ = self.validator._calculate_smart_date_score(inv, tx_3)
        self.assertGreaterEqual(s_3, 0.70)

        tx_30 = dict(self.tx_base, date='2024-02-14')
        s_30, _ = self.validator._calculate_smart_date_score(inv, tx_30)
        self.assertLessEqual(s_30, 0.30)

    def test_vendor_score_cases(self):
        inv = dict(self.invoice_base, vendor_name='Acme Corp')
        tx = dict(self.tx_base, description='Acme Corp')
        s_eq, _ = self.validator._calculate_smart_vendor_score(inv, tx)
        self.assertEqual(s_eq, 1.0)

        tx2 = dict(self.tx_base, description='Payment to Acme Corp services')
        s_incl, _ = self.validator._calculate_smart_vendor_score(inv, tx2)
        self.assertGreaterEqual(s_incl, 0.85)

        inv2 = dict(self.invoice_base, vendor_name='Xyz Inc')
        tx3 = dict(self.tx_base, description='Random content')
        s_zero, _ = self.validator._calculate_smart_vendor_score(inv2, tx3)
        self.assertLessEqual(s_zero, 0.3)

    def test_entity_score_mapping(self):
        inv = dict(self.invoice_base, business_unit='Delta Mining Paraguay')
        tx = dict(self.tx_base, classified_entity='paraguay ops delta mining')
        s_map, _ = self.validator._calculate_smart_entity_score(inv, tx)
        self.assertGreaterEqual(s_map, 0.8)

        inv2 = dict(self.invoice_base, business_unit='')
        tx2 = dict(self.tx_base, classified_entity='')
        s_missing, _ = self.validator._calculate_smart_entity_score(inv2, tx2)
        self.assertEqual(s_missing, 0.5)

    def test_pattern_score_invoice_in_description(self):
        inv = dict(self.invoice_base, invoice_number='INV-98765')
        tx = dict(self.tx_base, description='Paid INV-98765 via ACH')
        s, _ = self.validator._calculate_smart_pattern_score(inv, tx)
        self.assertEqual(s, 1.0)

    def test_sanity_checks_and_confidence(self):
        # Good match should pass sanity
        amt_s, _ = self.validator._calculate_smart_amount_score(self.invoice_base, self.tx_base)
        date_s, _ = self.validator._calculate_smart_date_score(self.invoice_base, self.tx_base)
        ven_s, _ = self.validator._calculate_smart_vendor_score(self.invoice_base, self.tx_base)
        ent_s, _ = self.validator._calculate_smart_entity_score(self.invoice_base, self.tx_base)
        pat_s, _ = self.validator._calculate_smart_pattern_score(self.invoice_base, self.tx_base)

        ok, warns = self.validator._perform_sanity_checks(self.invoice_base, self.tx_base, amt_s, date_s, ven_s)
        self.assertTrue(ok)

        conf = self.validator._determine_ai_confidence(amt_s, date_s, ven_s, ent_s, pat_s, ok)
        self.assertIsInstance(conf, str)
        self.assertNotEqual(conf.strip(), '')

    def test_evaluate_smart_match(self):
        crit = self.validator.evaluate_smart_match(self.invoice_base, self.tx_base)
        self.assertGreaterEqual(crit.amount_score, 0.5)
        self.assertTrue(isinstance(crit.overall_explanation, str))
        self.assertTrue(isinstance(crit.recommendation, str))


if __name__ == '__main__':
    unittest.main()
