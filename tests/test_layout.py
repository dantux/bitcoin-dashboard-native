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


if __name__ == "__main__":
    unittest.main()
