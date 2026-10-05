from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from orders.notifications.template_service import TemplateRenderer
from settings_manager.api.viewsets.email_template import EmailTemplateViewSet


class NotificationHTMLSafetyTests(SimpleTestCase):
    def test_custom_template_is_cleaned_after_layout_rendering(self):
        template = SimpleNamespace(
            subject_template="Nachricht",
            html_template="<p>{{ name }}</p>",
            text_template="",
            layout="general",
        )

        def unsafe_layout(layout, content, context, subject):
            return content + '<script>alert(1)</script><a href="java&#x73;cript:alert(1)">Link</a>'

        with patch.object(TemplateRenderer, "_apply_layout", side_effect=unsafe_layout):
            _, html, plain = TemplateRenderer._render_custom_template(template, {"name": "<b>Name</b>"})
        self.assertIn("&lt;b&gt;Name&lt;/b&gt;", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("javascript:", html)
        self.assertNotIn("alert(1)", plain)

    def test_default_template_preserves_reset_link_and_removes_active_content(self):
        with patch(
            "orders.notifications.template_service.render_to_string",
            return_value=(
                '<a href="https://example.test/reset?token=synthetic">Reset</a><iframe src="https://example.test"></iframe>'
            ),
        ):
            _, html, _ = TemplateRenderer._render_default_template("password_reset", {})
        self.assertIn('href="https://example.test/reset?token=synthetic"', html)
        self.assertNotIn("iframe", html)

    def test_admin_preview_removes_active_template_content(self):
        request = APIRequestFactory().post(
            "/preview/",
            {
                "subject_template": "Test",
                "html_template": '<p onclick="alert(1)">Text</p><script>alert(1)</script>',
            },
            format="json",
        )
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True, is_superuser=True))
        response = EmailTemplateViewSet.as_view({"post": "preview"})(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["html_content"], "<p>Text</p>")
