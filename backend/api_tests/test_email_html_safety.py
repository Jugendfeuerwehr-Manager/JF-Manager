"""Security regressions for personalized HTML email rendering."""

from django.test import SimpleTestCase

from members.models import Member
from members.services.email_service import EmailTemplateRenderer


class EmailHtmlSafetyTests(SimpleTestCase):
    def test_member_name_is_text_inside_html_template(self):
        member = Member(name='<img src=x onerror="alert(1)">', lastname="Test")

        rendered_html, rendered_text = EmailTemplateRenderer.render_for_member(
            "<p>Hallo {{vorname}}</p>", "Hallo {{vorname}}", member
        )

        self.assertIn("&lt;img", rendered_html)
        self.assertNotIn("<img", rendered_html)
        self.assertIn('<img src=x onerror="alert(1)">', rendered_text)

    def test_rich_text_preserves_formatting_but_drops_active_content(self):
        member = Member(name="Alex", lastname="Test")

        rendered_html, _ = EmailTemplateRenderer.render_for_member(
            '<p><strong>Hallo</strong><script>alert(1)</script><a href="javascript:alert(1)">Link</a></p>',
            "Hallo",
            member,
            signature='<p onclick="alert(1)">Viele Grüße</p>',
        )

        self.assertIn("<strong>Hallo</strong>", rendered_html)
        self.assertNotIn("<script", rendered_html)
        self.assertNotIn("javascript:", rendered_html)
        self.assertNotIn("onclick", rendered_html)
