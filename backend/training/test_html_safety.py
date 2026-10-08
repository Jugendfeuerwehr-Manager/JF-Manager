"""Stored training HTML is safe at both serializer boundaries."""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from training.api.serializers.block import TrainingBlockCreateSerializer, TrainingBlockSerializer
from training.api.serializers.library_block import LibraryBlockDetailSerializer, LibraryBlockExportSerializer
from training.models import LibraryBlock


class TrainingHtmlSafetyTests(SimpleTestCase):
    def test_block_input_and_legacy_output_are_sanitized(self):
        payload = '<p><strong>Übung</strong><a href="javascript:alert(1)">Info</a><script>bad()</script></p>'

        input_html = TrainingBlockCreateSerializer().fields["content"].to_internal_value(payload)
        output_html = TrainingBlockSerializer().fields["content"].to_representation(payload)

        for html in (input_html, output_html):
            self.assertIn("<strong>Übung</strong>", html)
            self.assertNotIn("javascript:", html)
            self.assertNotIn("<script", html)

    def test_library_input_and_export_strip_encoded_script_url(self):
        payload = '<p><a href="java&#x73;cript:alert(1)">Info</a></p>'

        input_html = LibraryBlockDetailSerializer().fields["content"].to_internal_value(payload)
        export_html = LibraryBlockExportSerializer().fields["content"].to_representation(payload)

        self.assertNotIn("javascript:", input_html)
        self.assertNotIn("javascript:", export_html)


class LibraryImportHtmlSafetyTests(TestCase):
    def test_federation_import_sanitizes_content_before_storage(self):
        user = get_user_model().objects.create_superuser("library-html-admin", "admin@example.test", "test-password")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            "/api/v1/training/library/import_blocks/",
            {
                "jf_manager_version": "1.0",
                "source_instance": "https://example.test/",
                "blocks": [
                    {
                        "export_uuid": str(uuid4()),
                        "title": "Übung",
                        "content": "<p><strong>Text</strong><script>bad()</script></p>",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        stored = LibraryBlock.objects.get(title="Übung")
        self.assertIn("<strong>Text</strong>", stored.content)
        self.assertNotIn("<script", stored.content)
