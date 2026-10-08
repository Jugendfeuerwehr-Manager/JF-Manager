"""NOTIF-01.3: notification e-mail catalogue, rendering, overrides and required links."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from notifications.email_catalog import CATALOG, PARTICIPATION_TYPES
from notifications.emails import NotFlatContext, missing_links, render
from orders.models import EmailTemplate

User = get_user_model()
XSS = '<script>alert("x")</script>'


class RenderTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_every_type_renders_with_its_sample_data(self):
        for kind, entry in CATALOG.items():
            with self.subTest(kind=kind):
                subject, html, text = render(kind, entry["sample_data"])
                self.assertTrue(subject and "\n" not in subject)
                self.assertIn(entry["sample_data"]["links"]["open"], html)
                if kind in PARTICIPATION_TYPES:
                    self.assertIn(entry["sample_data"]["links"]["withdraw"], html)
                    self.assertIn(entry["sample_data"]["links"]["withdraw_label"], text)
                if kind != "portal_invite":
                    self.assertIn("Benachrichtigungen einstellen", text)

    def test_text_part_keeps_link_targets(self):
        sample = CATALOG["waitlist_placed"]["sample_data"]
        _subject, _html, text = render("waitlist_placed", sample)
        self.assertIn(f"Von der Warteliste abmelden: {sample['links']['withdraw']}", text)
        self.assertIn(f"Benachrichtigungen einstellen: {sample['links']['preferences']}", text)

    def test_values_are_escaped(self):
        sample = {**CATALOG["waitlist_promoted"]["sample_data"]}
        sample["person"] = {"first_name": XSS}
        sample["session"] = {**sample["session"], "title": XSS}
        _subject, html, _text = render("waitlist_promoted", sample)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_only_flat_values(self):
        sample = {**CATALOG["cr_decided"]["sample_data"], "recipient": User(username="x")}
        with self.assertRaises(NotFlatContext):
            render("cr_decided", sample)

    def test_database_template_overrides_and_reset(self):
        template = EmailTemplate.objects.create(
            name="Eigene",
            template_type="session_published",
            subject_template="Eigener Betreff {{ session.title }}",
            html_template="<p>Eigen</p>{% include 'notifications/emails/_footer.html' %}",
            layout="none",
        )
        self.assertEqual(
            render("session_published", CATALOG["session_published"]["sample_data"])[0],
            "Eigener Betreff Knoten und Stiche",
        )
        template.delete()
        cache.clear()
        self.assertTrue(
            render("session_published", CATALOG["session_published"]["sample_data"])[0].startswith("Neuer Termin")
        )

    def test_required_links(self):
        self.assertEqual(
            missing_links("session_published", "<p>{{ links.open }}</p>"),
            ["links.preferences", "links.withdraw", "links.withdraw_label"],
        )
        self.assertEqual(missing_links("cr_decided", "{{links.open}} {{ links.preferences }}"), [])
        self.assertEqual(missing_links("order_created", "<p>ohne</p>"), [])  # not a notification type


class SettingsApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_superuser("admin", password="x"))

    def test_types_variables_and_default_content(self):
        types = {t["value"] for t in self.client.get("/api/v1/settings/email-templates/types/").json()}
        self.assertLessEqual(set(CATALOG), types)
        variables = self.client.get(
            "/api/v1/settings/email-templates/variables/?template_type=session_published"
        ).json()
        self.assertIn("required_links", variables)
        self.assertEqual(variables["sample_data"]["session"]["title"], "Knoten und Stiche")
        default = self.client.get(
            "/api/v1/settings/email-templates/default_content/?template_type=waitlist_placed"
        ).json()
        self.assertIn("_footer.html", default["html_template"])

    def test_saving_without_required_links_is_rejected(self):
        payload = {
            "name": "Kaputt",
            "template_type": "waitlist_placed",
            "subject_template": "Warteliste",
            "html_template": "<p>{{ links.open }}</p>",
            "layout": "none",
            "is_active": True,
        }
        response = self.client.post("/api/v1/settings/email-templates/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("links.withdraw", str(response.json()))
        default = self.client.get(
            "/api/v1/settings/email-templates/default_content/?template_type=waitlist_placed"
        ).json()
        payload["html_template"] = default["html_template"]
        self.assertEqual(self.client.post("/api/v1/settings/email-templates/", payload, format="json").status_code, 201)
