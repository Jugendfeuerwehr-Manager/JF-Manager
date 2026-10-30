"""DSGVO: the Django admin offers no bulk import/export of personal data.

Exports run through the API, which scopes by department, asks for step-up and
writes an ExportAudit; the admin bypasses all three.
"""

from django.contrib import admin
from django.test import SimpleTestCase
from django.urls import NoReverseMatch, reverse


class AdminBulkExportTests(SimpleTestCase):
    def test_no_admin_offers_import_or_export(self):
        offenders = [
            f"{model._meta.label}: {type(model_admin).__name__}"
            for model, model_admin in admin.site._registry.items()
            if any(cls.__module__.startswith("import_export") for cls in type(model_admin).__mro__)
        ]
        self.assertEqual(offenders, [])

    def test_member_export_route_is_gone(self):
        for name in ("admin:members_member_export", "admin:members_parent_import"):
            with self.subTest(name=name), self.assertRaises(NoReverseMatch):
                reverse(name)
