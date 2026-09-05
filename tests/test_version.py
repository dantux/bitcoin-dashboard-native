import unittest

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import app
from app import dashboard_version, format_header_eyebrow, format_knots_version


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


class DashboardVersionTests(unittest.TestCase):
    def test_dashboard_version_prefers_app_version_env(self):
        with patch.dict(os.environ, {"APP_VERSION": "9.9.9"}, clear=True):
            self.assertEqual(dashboard_version(), "9.9.9")

    def test_dashboard_version_reads_version_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "VERSION"
            path.write_text("1.2.3\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch.object(
                app, "APP_DIR", Path(directory)
            ):
                self.assertEqual(dashboard_version(), "1.2.3")
