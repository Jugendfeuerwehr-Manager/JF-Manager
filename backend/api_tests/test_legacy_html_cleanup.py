from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from jf_manager_backend.html_safety import sanitize_rich_html


class LegacyHTMLCleanupTests(TestCase):
    def test_dry_run_apply_and_idempotent_repeat(self):
        user = get_user_model().objects.create(username="html-cleanup", email_signature='<p onclick="bad()">Hello</p>')
        output = StringIO()
        call_command("sanitize_legacy_html", stdout=output)
        user.refresh_from_db()
        self.assertIn("onclick", user.email_signature)
        self.assertIn("1 zu bereinigen", output.getvalue())
        call_command("sanitize_legacy_html", apply=True, stdout=StringIO())
        user.refresh_from_db()
        self.assertEqual(user.email_signature, "<p>Hello</p>")
        repeat = StringIO()
        call_command("sanitize_legacy_html", apply=True, stdout=repeat)
        self.assertNotIn("1 migriert", repeat.getvalue())

    def test_safe_mail_layout_and_unsafe_css_values(self):
        html = sanitize_rich_html(
            '<table width="600"><tr><td style="color:#333; padding:20px; position:fixed">Text</td></tr></table>'
        )
        self.assertIn('width="600"', html)
        self.assertIn("color:#333", html)
        self.assertIn("padding:20px", html)
        self.assertNotIn("position", html)
        for css in ("width:expression(alert(1))", "color:r\\65 d", "background-color:url(https://example.test)"):
            self.assertNotIn("style=", sanitize_rich_html(f'<p style="{css}">Text</p>'))
        self.assertIn(
            'src="https://example.test/logo.png"',
            sanitize_rich_html('<img src="https://example.test/logo.png" onerror="bad()">'),
        )
