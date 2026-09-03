import unittest

from app import format_header_eyebrow, format_knots_version


class KnotsVersionTests(unittest.TestCase):
    def test_formats_knots_user_agent(self):
        self.assertEqual(
            format_knots_version("/Satoshi:29.3.0/Knots:20260210/"),
            "29.3.0 / Knots 20260210",
        )

    def test_formats_satoshi_only_user_agent(self):
        self.assertEqual(format_knots_version("/Satoshi:28.1.0/"), "28.1.0")

    def test_returns_none_for_missing_user_agent(self):
        self.assertIsNone(format_knots_version(None))
        self.assertIsNone(format_knots_version(""))

    def test_header_eyebrow_includes_version_and_host(self):
        self.assertEqual(
            format_header_eyebrow("29.3.0 / Knots 20260210"),
            "Bitcoin Knots · 29.3.0 (Knots 20260210) · knots-pi5",
        )

    def test_header_eyebrow_falls_back_without_version(self):
        self.assertEqual(format_header_eyebrow(None), "Bitcoin Knots · knots-pi5")
