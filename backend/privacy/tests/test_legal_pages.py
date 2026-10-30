"""DSGVO: imprint and privacy notice are edited as drafts and published as versions. Fictional data."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from privacy.models import LegalPageVersion

User = get_user_model()
BASE = "/api/v1/privacy/legal-pages/"


class LegalPageEditorTests(APITestCase):
    def setUp(self):
        self.editor = User.objects.create_user("datenschutz", password="x")
        self.editor.user_permissions.add(
            *Permission.objects.filter(codename__in=["view_privacy_settings", "change_privacy_settings"])
        )
        self.reader = User.objects.create_user("leser", password="x")
        self.reader.user_permissions.add(Permission.objects.get(codename="view_privacy_settings"))
        self.nobody = User.objects.create_user("ohne-recht", password="x")

    def test_anonymous_and_accounts_without_right_are_rejected(self):
        self.assertIn(self.client.get(BASE).status_code, (401, 403))
        self.client.force_authenticate(self.nobody)
        self.assertEqual(self.client.get(BASE).status_code, 403)
        self.assertEqual(self.client.patch(f"{BASE}privacy/", {"draft_title": "x"}).status_code, 403)

    def test_read_right_does_not_allow_editing_or_publishing(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get(BASE).status_code, 200)
        self.assertEqual(self.client.patch(f"{BASE}privacy/", {"draft_title": "x"}).status_code, 403)
        self.assertEqual(self.client.post(f"{BASE}privacy/publish/").status_code, 403)

    def test_draft_publish_and_versions(self):
        self.client.force_authenticate(self.editor)
        pages = self.client.get(BASE).json()
        self.assertEqual({page["kind"] for page in pages}, {"imprint", "privacy"})

        draft = self.client.patch(
            f"{BASE}privacy/",
            {"draft_title": "Datenschutz", "draft_body": '<p onclick="x()">Text</p><script>alert(1)</script>'},
            format="json",
        ).json()
        self.assertEqual(draft["draft_body"], "<p>Text</p>")
        self.assertTrue(draft["has_unpublished_changes"])
        self.assertIsNone(draft["current_version"])
        self.assertEqual(self.client.get("/api/v1/legal/privacy/").status_code, 404)

        published = self.client.post(f"{BASE}privacy/publish/", {"change_note": "Erstfassung"}, format="json")
        self.assertEqual(published.status_code, 201, published.content)
        self.assertEqual(published.json()["current_version"]["version"], 1)
        self.assertFalse(published.json()["has_unpublished_changes"])
        # Publishing the unchanged draft again creates no empty version.
        self.assertEqual(self.client.post(f"{BASE}privacy/publish/").status_code, 400)

        self.client.patch(f"{BASE}privacy/", {"draft_body": "<p>Neu</p>"}, format="json")
        self.client.post(f"{BASE}privacy/publish/")
        versions = self.client.get(f"{BASE}privacy/versions/").json()
        self.assertEqual([v["version"] for v in versions], [2, 1])
        self.assertEqual(versions[1]["body"], "<p>Text</p>")  # old versions stay as evidence

    def test_empty_draft_cannot_be_published(self):
        self.client.force_authenticate(self.editor)
        self.client.patch(f"{BASE}imprint/", {"draft_body": ""}, format="json")
        self.assertEqual(self.client.post(f"{BASE}imprint/publish/").status_code, 400)
        self.assertFalse(LegalPageVersion.objects.exists())

    def test_unknown_kind_is_not_routed(self):
        self.client.force_authenticate(self.editor)
        self.assertEqual(self.client.get(f"{BASE}cookies/").status_code, 404)


class PublicLegalPageTests(APITestCase):
    def setUp(self):
        from privacy.models import LegalPage
        from privacy.services import legal

        page = legal.get_page(LegalPage.Kind.IMPRINT)
        legal.save_draft(page, title="Impressum", body="<p>Jugendfeuerwehr Musterstadt</p>", user=None)
        legal.publish(page, user=None)

    def test_published_text_is_public_and_listed_in_branding(self):
        response = self.client.get("/api/v1/legal/imprint/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Impressum")
        self.assertEqual(self.client.get("/api/v1/app/branding/").json()["legal"], {"imprint": True, "privacy": False})

    def test_portal_accounts_can_read_it(self):
        portal = User.objects.create_user("eltern@example.org", password="x", account_kind=User.AccountKind.PORTAL)
        self.client.force_login(portal)
        self.assertEqual(self.client.get("/api/v1/legal/imprint/").status_code, 200)

    def test_drafts_never_leak(self):
        from privacy.models import LegalPage
        from privacy.services import legal

        legal.save_draft(legal.get_page(LegalPage.Kind.IMPRINT), title="Geheim", body="<p>Entwurf</p>", user=None)
        self.assertEqual(self.client.get("/api/v1/legal/imprint/").json()["title"], "Impressum")
