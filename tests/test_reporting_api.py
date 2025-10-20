import os
import sys
import types
import unittest
try:
    from flask import Flask
except ImportError:  # pragma: no cover - environment without Flask
    Flask = None


def _install_stubs():
    # Stub psycopg2
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

    # Stub dotenv
    dotenv = types.SimpleNamespace()
    def load_dotenv(*args, **kwargs):
        return False
    dotenv.load_dotenv = load_dotenv
    sys.modules.setdefault('dotenv', dotenv)

    # Stub reportlab (not used in tested endpoints but imported)
    reportlab = types.SimpleNamespace()
    reportlab.lib = types.SimpleNamespace(pagesizes=types.SimpleNamespace(letter=None, A4=None),
                                          styles=types.SimpleNamespace(getSampleStyleSheet=lambda: None, ParagraphStyle=object),
                                          units=types.SimpleNamespace(inch=1),
                                          colors=types.SimpleNamespace(HexColor=lambda x: x))
    reportlab.platypus = types.SimpleNamespace(SimpleDocTemplate=object, Paragraph=object, Spacer=object, Table=object, TableStyle=object)
    sys.modules.setdefault('reportlab', reportlab)
    sys.modules.setdefault('reportlab.lib', reportlab.lib)
    sys.modules.setdefault('reportlab.lib.pagesizes', reportlab.lib.pagesizes)
    sys.modules.setdefault('reportlab.lib.styles', reportlab.lib.styles)
    sys.modules.setdefault('reportlab.lib.units', reportlab.lib.units)
    sys.modules.setdefault('reportlab.lib.colors', reportlab.lib.colors)
    sys.modules.setdefault('reportlab.platypus', reportlab.platypus)

    # Stub reporting.financial_statements for income-statement endpoint
    fs_mod = types.ModuleType('reporting.financial_statements')
    class FinancialStatementsGenerator:
        def generate_income_statement(self, period_id=None, start_date=None, end_date=None, comparison_period_id=None, include_details=False):
            return {'summary': {'revenue': 1000.0, 'expenses': 200.0, 'net_income': 800.0}}
    fs_mod.FinancialStatementsGenerator = FinancialStatementsGenerator
    sys.modules.setdefault('reporting.financial_statements', fs_mod)

    # Stub heavy web_ui modules imported by reporting_api
    pdf_reports = types.ModuleType('DeltaCFOAgent.web_ui.pdf_reports')
    class DREReport: pass
    class BalanceSheetReport: pass
    pdf_reports.DREReport = DREReport
    pdf_reports.BalanceSheetReport = BalanceSheetReport
    sys.modules.setdefault('DeltaCFOAgent.web_ui.pdf_reports', pdf_reports)

    cfr_mod = types.ModuleType('DeltaCFOAgent.web_ui.cash_flow_report_new')
    class CashFlowReport: pass
    cfr_mod.CashFlowReport = CashFlowReport
    sys.modules.setdefault('DeltaCFOAgent.web_ui.cash_flow_report_new', cfr_mod)

    dmpl_mod = types.ModuleType('DeltaCFOAgent.web_ui.dmpl_report_new')
    class DMPLReport: pass
    dmpl_mod.DMPLReport = DMPLReport
    sys.modules.setdefault('DeltaCFOAgent.web_ui.dmpl_report_new', dmpl_mod)


@unittest.skipIf(Flask is None, "Flask not installed; skipping API route tests")
class TestReportingAPI(unittest.TestCase):
    def setUp(self):
        _install_stubs()
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_DB_PATH'] = 'test_reporting.sqlite'

        # Ensure fresh imports
        for mod in list(sys.modules.keys()):
            if mod.startswith('DeltaCFOAgent.web_ui.database') or mod.startswith('DeltaCFOAgent.web_ui.reporting_api'):
                sys.modules.pop(mod)

        from DeltaCFOAgent.web_ui import reporting_api  # type: ignore
        self.reporting_api = reporting_api

        # Build isolated Flask app and register routes
        self.app = Flask(__name__)
        self.reporting_api.register_reporting_routes(self.app)
        self.client = self.app.test_client()

        # Monkeypatch db_manager.execute_query for the simple endpoint
        def fake_execute_query(query, params=None, fetch_one=False, fetch_all=False):
            text = (query or '').lower()
            if 'where amount > 0' in text:
                return [
                    {'category': 'Sales', 'total': 700.0, 'count': 7},
                    {'category': 'Other', 'total': 300.0, 'count': 3},
                ]
            if 'where amount < 0' in text:
                return [
                    {'category': 'General & Administrative', 'total': 150.0, 'count': 5},
                    {'category': 'R&D', 'total': 50.0, 'count': 2},
                ]
            if fetch_one:
                return {'health_check': 1}
            return []

        reporting_api.db_manager.execute_query = fake_execute_query  # type: ignore

    def tearDown(self):
        os.environ.pop('DB_TYPE', None)
        os.environ.pop('SQLITE_DB_PATH', None)

    def test_income_statement_simple(self):
        resp = self.client.get('/api/reports/income-statement/simple')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        stmt = data.get('statement', {})
        self.assertIn('revenue', stmt)
        self.assertIn('operating_income', stmt)
        self.assertIn('revenue', stmt)
        self.assertGreaterEqual(stmt.get('revenue', {}).get('total', 0), 0)

    def test_income_statement_full(self):
        resp = self.client.post('/api/reports/income-statement', json={'include_details': False})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('statement', data)

    def test_income_statement_bad_start_date_post(self):
        resp = self.client.post('/api/reports/income-statement', json={'start_date': 'BADDATE', 'end_date': '2024-01-31'})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn('Invalid start_date format', data.get('error', ''))

    def test_income_statement_bad_end_date_post(self):
        resp = self.client.post('/api/reports/income-statement', json={'start_date': '2024-01-01', 'end_date': '31/01/2024'})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn('Invalid end_date format', data.get('error', ''))

    def test_income_statement_bad_dates_post(self):
        resp = self.client.post('/api/reports/income-statement', json={'start_date': '2024/01/01', 'end_date': 'BAD'})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertTrue('Invalid' in data.get('error', ''))


if __name__ == '__main__':
    unittest.main()
