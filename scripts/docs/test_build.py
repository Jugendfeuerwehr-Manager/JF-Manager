"""Exercise delivery validation against broken targets and external assets."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build


class DeliveryValidationTest(unittest.TestCase):
    def validate(self, markup, other=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text(markup)
            if other:
                (root / "article.html").write_text(other)
            with patch.object(build, "SITE", root):
                build.check_site()

    def test_relative_article_and_anchor(self):
        self.validate(
            '<a href="article.html#steps">Read</a>', '<h1 id="steps">Steps</h1>'
        )

    def test_missing_page_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, "missing target"):
            self.validate('<a href="lost.html">Lost</a>')

    def test_missing_anchor_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, "missing anchor"):
            self.validate(
                '<a href="article.html#lost">Lost</a>', '<h1 id="steps">Steps</h1>'
            )

    def test_external_runtime_asset_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, "external runtime asset"):
            self.validate('<script src="https://cdn.example.invalid/app.js"></script>')

    def test_external_reference_is_allowed(self):
        self.validate('<a href="https://example.invalid/reference">Reference</a>')

    def test_link_cannot_escape_delivery(self):
        with self.assertRaisesRegex(SystemExit, "missing target"):
            self.validate('<a href="../index.html">Outside</a>')


if __name__ == "__main__":
    unittest.main()
