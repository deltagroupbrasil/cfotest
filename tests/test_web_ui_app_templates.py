"""
Plan:
- Render dashboard '/' and '/dashboard' and check key HTML elements exist.
- Render '/revenue' and ensure template content and cache buster in HTML.
- Verify static assets load (status 200) for core CSS/JS paths.
"""

import unittest
try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

from DeltaCFOAgent.web_ui import app as appmod


@unittest.skipIf(BeautifulSoup is None, "bs4 not installed; skipping template parsing tests")
class TestAppTemplates(unittest.TestCase):
    def setUp(self):
        self.client = appmod.app.test_client()

    def _assert_has_buttons_and_sections(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        # Expect nav or header elements common to the dashboard
        self.assertTrue(soup.find(['nav', 'header']))
        # Expect at least one button in the UI
        self.assertTrue(soup.find('button'))
        # Expect file upload or filters sections to exist in templates
        self.assertTrue(soup.find(attrs={'id': lambda v: v and 'filter' in v.lower()}) or soup.find('form'))

    def test_home_dashboard_renders(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self._assert_has_buttons_and_sections(html)

    def test_dashboard_alias_renders(self):
        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self._assert_has_buttons_and_sections(html)

    def test_revenue_page_renders(self):
        resp = self.client.get('/revenue')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self._assert_has_buttons_and_sections(html)
        # cache_buster query expected on assets
        self.assertIn('cache_buster', html)

    def test_static_assets(self):
        # These exist in repo under web_ui/static
        for path in (
            '/static/style.css',
            '/static/script.js',
            '/static/cfo_dashboard.css',
            '/static/cfo_dashboard.js',
        ):
            r = self.client.get(path)
            self.assertEqual((path, r.status_code), (path, 200))


if __name__ == '__main__':
    unittest.main()
