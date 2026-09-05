from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


class HeadingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_h2 = False
        self.headings = []

    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self.in_h2 = True

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_h2 = False

    def handle_data(self, data):
        if self.in_h2 and data.strip():
            self.headings.append(data.strip())


class MainPageLayoutTests(unittest.TestCase):
    def test_latest_blocks_appears_before_services(self):
        parser = HeadingParser()
        parser.feed(Path("index.html").read_text())

        self.assertLess(
            parser.headings.index("Latest Blocks"),
            parser.headings.index("Services"),
        )

    def test_services_panel_includes_knots_version(self):
        html = Path("index.html").read_text()
        js = Path("app.js").read_text()

        self.assertIn('<div><dt>Version</dt><dd id="knots-version">--</dd></div>', html)
        self.assertIn('knots-version', js)

    def test_header_includes_knots_version_eyebrow(self):
        html = Path("index.html").read_text()
        js = Path("app.js").read_text()

        self.assertIn('id="node-eyebrow"', html)
        self.assertIn("Bitcoin Knots · knots-pi5", html)
        self.assertIn("node-eyebrow", js)
        self.assertIn("formatHeaderEyebrow", js)

    def test_desktop_metric_cards_use_one_grid_row(self):
        html = Path("index.html").read_text()
        metric_count = len(re.findall(r'<article class="metric">', html))
        css = Path("styles.css").read_text()
        desktop_rule = re.search(r"\.metric-grid\s*\{([^}]*)\}", css, re.DOTALL)

        if desktop_rule is None:
            self.fail("Desktop .metric-grid rule is missing")
        self.assertEqual(metric_count, 8)
        self.assertIn(
            f"grid-template-columns: repeat({metric_count}, minmax(0, 1fr));",
            desktop_rule.group(1),
        )

    def test_page_footer_shows_dashboard_version(self):
        html = Path("index.html").read_text()
        js = Path("app.js").read_text()

        self.assertGreater(html.index("<footer"), html.index("<h2>Peers</h2>"))
        self.assertIn('id="dashboard-version"', html)
        self.assertIn("dashboard-version", js)


if __name__ == "__main__":
    unittest.main()
