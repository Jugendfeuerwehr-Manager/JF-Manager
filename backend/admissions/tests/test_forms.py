"""Application form builder: schema rules, publishing and the forms API. Fictional data."""

import copy

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from admissions.models import AdmissionForm, AdmissionTextBlock
from admissions.schema import check_structure
from admissions.services import forms as form_service
from departments.models import Department
from membership.tests.test_lifecycle import role
from privacy.models import LegalPage
from privacy.services import legal

User = get_user_model()


def publish_privacy_text():
    page = legal.get_page(LegalPage.Kind.PRIVACY)
    legal.save_draft(page, title="Datenschutzerklärung", body="<p>Wir verarbeiten …</p>", user=None)
    return legal.publish(page, user=None)


def element(schema, element_id):
    return next(
        el
        for page in schema["pages"]
        for section in page["sections"]
        for el in section["elements"]
        if el["id"] == element_id
    )


def single_section(*elements):
    return {"pages": [{"id": "p", "title": "S", "sections": [{"id": "s", "title": "A", "elements": list(elements)}]}]}


class SchemaRuleTests(TestCase):
    def test_sample_form_is_valid(self):
        self.assertEqual(form_service.check(form_service.template_for(None), for_publish=True), [])

    def test_empty_form_cannot_be_published(self):
        self.assertTrue(form_service.check({"pages": []}, for_publish=True))
        self.assertEqual(form_service.check({"pages": []}), [])

    def test_broken_structure_is_reported(self):
        self.assertTrue(check_structure({"pages": [{"sections": "x"}]}))
        self.assertTrue(check_structure(single_section({"type": "unknown", "id": "a"})))

    def test_duplicate_keys_and_targets_are_rejected(self):
        schema = single_section(
            {"id": "a", "type": "text", "key": "vorname", "label": "Vorname", "target": "member.name"},
            {"id": "b", "type": "text", "key": "vorname", "label": "Rufname", "target": "member.name"},
        )
        messages = " ".join(error["message"] for error in form_service.check(schema))
        self.assertIn("doppelt", messages)
        self.assertIn("schon einem anderen Feld", messages)

    def test_target_must_match_the_element_type(self):
        schema = single_section({"id": "a", "type": "checkbox", "key": "x", "label": "X", "target": "member.birthday"})
        self.assertTrue(form_service.check(schema))

    def test_choices_need_options(self):
        schema = single_section({"id": "a", "type": "select", "key": "x", "label": "X", "options": []})
        self.assertTrue(form_service.check(schema))

    def test_unknown_consent_kind_is_rejected(self):
        schema = single_section({"id": "a", "type": "consent", "key": "x", "label": "X", "consent_kind": "nope"})
        self.assertTrue(form_service.check(schema))

    def test_visibility_may_only_depend_on_earlier_fields(self):
        schema = single_section(
            {"id": "a", "type": "text", "key": "x", "label": "X", "visible_if": {"field": "later", "equals": "1"}},
            {"id": "b", "type": "text", "key": "later", "label": "Y"},
        )
        self.assertTrue(form_service.check(schema))

    def test_guardians_need_names(self):
        schema = single_section(
            {"id": "a", "type": "guardians", "key": "g", "label": "G", "fields": [{"target": "guardian.email"}]}
        )
        self.assertTrue(form_service.check(schema))


class PublishTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Mitte", code="af-mitte")
        self.form = form_service.create_form(department=self.department, title="Aufnahmeantrag")

    def test_publish_requires_published_legal_texts(self):
        with self.assertRaises(ValidationError):
            form_service.publish(self.form)

    def test_publish_freezes_legal_text_consent_wording_and_text_blocks(self):
        publish_privacy_text()
        block = AdmissionTextBlock.objects.create(department=self.department, title="Hinweis", body="<p>Alt</p>")
        schema = copy.deepcopy(self.form.draft_schema)
        element(schema, "e_photo_hint").update({"text_block": block.pk, "html": ""})
        form_service.save_draft(self.form, schema)

        version = form_service.publish(self.form, change_note="Erste Fassung")
        block.body = "<p>Neu</p>"
        block.save()

        self.assertEqual(version.version, 1)
        self.assertEqual(element(version.schema, "e_privacy")["legal"]["version"], "privacy:v1")
        self.assertIn("Verwaltungszwecken", element(version.schema, "e_data_applicant")["consent"]["text"])
        self.assertEqual(element(version.schema, "e_photo_hint")["html"], "<p>Alt</p>")
        self.assertEqual(len(version.schema_hash), 64)

    def test_versions_are_immutable_and_numbered(self):
        publish_privacy_text()
        first = form_service.publish(self.form)
        self.form.title = "Aufnahmeantrag 2027"
        self.form.save()
        second = form_service.publish(self.form)
        self.assertEqual((first.version, second.version), (1, 2))
        self.assertNotEqual(first.schema_hash, second.schema_hash)
        first.title = "x"
        with self.assertRaises(DjangoValidationError):
            first.save()


class FormApiTests(APITestCase):
    URL = "/api/v1/admissions/forms/"

    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="afa-mitte")
        self.nord = Department.objects.create(name="Nord", code="afa-nord")
        self.form = form_service.create_form(department=self.mitte, title="Aufnahmeantrag")
        publish_privacy_text()

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.get(self.URL).status_code, (401, 403))

    def test_missing_right_is_refused(self):
        self.client.force_authenticate(self.user("ohne", self.mitte, "view_member"))
        self.assertEqual(self.client.get(self.URL).status_code, 403)

    def test_foreign_department_sees_nothing(self):
        self.client.force_authenticate(self.user("nord", self.nord, "view_admissionform", "change_admissionform"))
        self.assertEqual(self.client.get(self.URL).json()["count"], 0)
        response = self.client.patch(f"{self.URL}{self.form.pk}/", {"title": "x"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_editor_creates_from_template_and_saves_draft(self):
        self.client.force_authenticate(
            self.user("leiter", self.mitte, "view_admissionform", "add_admissionform", "change_admissionform")
        )
        response = self.client.post(self.URL, {"title": "Neu", "department": self.mitte.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertTrue(body["draft_schema"]["pages"])
        self.assertEqual(body["draft_issues"], [])

        response = self.client.patch(f"{self.URL}{body['id']}/", {"draft_schema": {"pages": "x"}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_editor_cannot_create_in_foreign_department(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_admissionform", "add_admissionform"))
        response = self.client.post(self.URL, {"title": "Neu", "department": self.nord.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AdmissionForm.objects.filter(department=self.nord).exists())

    def test_publish_needs_its_own_right(self):
        editor = self.user("leiter", self.mitte, "view_admissionform", "change_admissionform")
        self.client.force_authenticate(editor)
        self.assertEqual(self.client.post(f"{self.URL}{self.form.pk}/publish/").status_code, 403)

        publisher = self.user("jugendwart", self.mitte, "view_admissionform", "publish_admissionform")
        self.client.force_authenticate(publisher)
        response = self.client.post(f"{self.URL}{self.form.pk}/publish/", {"change_note": "Start"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.client.get(f"{self.URL}{self.form.pk}/versions/").json()[0]["version"], 1)

    def test_references_list_catalog_and_consent_kinds(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_admissionform"))
        body = self.client.get(f"{self.URL}references/").json()
        self.assertIn("member.birthday", {field["key"] for field in body["fields"]["member"]})
        self.assertIn("consent_continues_ea", {kind["slug"] for kind in body["consent_kinds"]})
        self.assertIn("portal_terms", {kind["value"] for kind in body["legal_kinds"]})


class DraftSanitizingTests(APITestCase):
    def test_rich_text_in_drafts_is_cleaned_on_save(self):
        department = Department.objects.create(name="Mitte", code="afs-mitte")
        form = form_service.create_form(department=department, title="Antrag", from_template=False)
        user = User.objects.create_user("leiter", password="x")
        role(user, department, "view_admissionform", "change_admissionform")
        self.client.force_authenticate(user)
        schema = single_section(
            {"id": "a", "type": "richtext", "html": '<p onclick="x()">Hi</p><script>alert(1)</script>'}
        )
        response = self.client.patch(f"/api/v1/admissions/forms/{form.pk}/", {"draft_schema": schema}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        html = response.json()["draft_schema"]["pages"][0]["sections"][0]["elements"][0]["html"]
        self.assertNotIn("script", html)
        self.assertNotIn("onclick", html)
