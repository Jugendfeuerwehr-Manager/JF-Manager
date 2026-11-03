"""Answers that reach the member, organisation forms and public links. Fictional data."""

import json
import shutil

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from admissions.models import AdmissionForm, Application
from admissions.services import decisions, vouchers
from admissions.services import forms as form_service
from admissions.services.takeover import take_over
from admissions.tests.test_applications import MEDIA, PUBLIC, child_answers
from admissions.tests.test_forms import publish_privacy_text, single_section
from departments.models import Department
from members.models import MemberFieldDefinition
from membership.tests.test_lifecycle import role

User = get_user_model()
FORMS = "/api/v1/admissions/forms/"
VOUCHERS = "/api/v1/admissions/vouchers/"


def text(key, **extra):
    return {"id": key, "type": "text", "key": key, "label": key.title(), **extra}


class TargetRuleTests(TestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="tr-mitte")
        MemberFieldDefinition.objects.create(key="schule", label="Schule")
        MemberFieldDefinition.objects.create(key="spind", label="Spind", department=self.mitte)

    def messages(self, schema, department_id=None):
        return [issue["message"] for issue in form_service.check(schema, department_id)]

    def test_inputs_without_target_are_lost_and_rejected(self):
        self.assertIn(
            "Diese Angabe landet nicht am Mitglied. Bitte ein Mitglieds- oder Zusatzfeld zuordnen.",
            self.messages(single_section(text("hobby"))),
        )

    def test_required_confirmation_may_stay_in_the_application(self):
        confirmation = {"id": "c", "type": "checkbox", "key": "ok", "label": "Gelesen", "required": True}
        self.assertEqual(self.messages(single_section(confirmation)), [])

    def test_additional_fields_follow_the_form_scope(self):
        schema = single_section(
            text("schule", target="member.extra.schule"), text("spind", target="member.extra.spind")
        )
        self.assertEqual(self.messages(schema, self.mitte.pk), [])
        # Organisation forms serve every department, so a department field is not offered.
        self.assertEqual(len(self.messages(schema)), 1)

    def test_single_use_elements_are_reported_twice(self):
        schema = single_section(
            {"id": "a", "type": "signature", "key": "u1", "role": "applicant", "required": True},
            {"id": "b", "type": "signature", "key": "u2", "role": "applicant", "required": True},
            {"id": "c", "type": "legal_ack", "key": "d1", "label": "DS", "legal_kind": "privacy"},
            {"id": "d", "type": "legal_ack", "key": "d2", "label": "DS", "legal_kind": "privacy"},
        )
        messages = self.messages(schema)
        self.assertIn("Diese Unterschrift kommt schon im Formular vor.", messages)
        self.assertIn("Dieser Rechtstext kommt schon im Formular vor.", messages)

    def test_unpublished_legal_text_shows_up_before_publishing(self):
        form = form_service.create_form(department=self.mitte, title="Antrag")
        issues = form_service.draft_issues(form)
        self.assertIn("Der Rechtstext ist noch nicht veröffentlicht.", [issue["message"] for issue in issues])
        publish_privacy_text()
        self.assertEqual(form_service.draft_issues(form), [])

    def test_template_keeps_free_fields_only_with_a_matching_additional_field(self):
        MemberFieldDefinition.objects.create(key="vereine", label="Vereine", field_type="textarea")
        keys = {
            element.get("target")
            for page in form_service.template_for(None)["pages"]
            for section in page["sections"]
            for element in section["elements"]
        }
        self.assertIn("member.extra.vereine", keys)


class OrganisationFormApiTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="of-mitte")
        self.nord = Department.objects.create(name="Nord", code="of-nord")
        publish_privacy_text()
        self.org_form = form_service.create_form(department=None, title="Organisation")
        form_service.publish(self.org_form)

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def org_user(self, *codenames):
        user = User.objects.create_user("orga", password="x")
        user.user_permissions.add(*Permission.objects.filter(codename__in=["can_access_all_departments", *codenames]))
        return user

    def test_department_staff_sees_but_cannot_change_organisation_forms(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_admissionform", "change_admissionform"))
        self.assertEqual(self.client.get(FORMS).json()["count"], 1)
        # The frontend always sends its department context.
        response = self.client.get(f"{FORMS}{self.org_form.pk}/", {"department": self.mitte.pk})
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(f"{FORMS}{self.org_form.pk}/", {"title": "x"}, format="json")
        self.assertIn(response.status_code, (400, 403))
        self.org_form.refresh_from_db()
        self.assertEqual(self.org_form.title, "Organisation")
        response = self.client.post(FORMS, {"title": "Neu", "department": None}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_organisation_wide_editor_creates_organisation_forms(self):
        self.client.force_authenticate(self.org_user("view_admissionform", "add_admissionform", "change_admissionform"))
        response = self.client.post(FORMS, {"title": "Neu", "department": None}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(AdmissionForm.objects.get(pk=response.json()["id"]).department_id)

    def test_voucher_of_an_organisation_form_names_its_department(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_admissionvoucher", "add_admissionvoucher"))
        response = self.client.post(VOUCHERS, {"form": self.org_form.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post(VOUCHERS, {"form": self.org_form.pk, "department": self.nord.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post(VOUCHERS, {"form": self.org_form.pk, "department": self.mitte.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["department"], self.mitte.pk)


@override_settings(MEDIA_ROOT=MEDIA)
class PublicFormTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.mitte = Department.objects.create(name="Mitte", code="pf-mitte")
        self.nord = Department.objects.create(name="Nord", code="pf-nord")
        self.hidden = Department.objects.create(name="Einsatzabteilung", code="pf-ea")
        MemberFieldDefinition.objects.create(key="schule", label="Schule")
        publish_privacy_text()
        self.form = form_service.create_form(department=None, title="Aufnahme")
        schema = self.form.draft_schema
        schema["pages"][0]["sections"][0]["elements"].append(text("schule", target="member.extra.schule"))
        form_service.save_draft(self.form, schema)
        self.form.access = AdmissionForm.Access.PUBLIC
        self.form.public_slug = form_service.new_public_slug(self.form.title)
        self.form.save()
        self.form.public_departments.set([self.mitte, self.nord])
        form_service.publish(self.form)
        self.url = f"{PUBLIC}form/{self.form.public_slug}/"

    def post(self, department, **extra):
        body = {"answers": child_answers(schule="Realschule"), "department": department, **extra}
        return self.client.post(self.url, body, format="json")

    def test_only_the_chosen_departments_are_named(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([d["name"] for d in response.json()["departments"]], ["Mitte", "Nord"])

    def test_voucher_only_forms_have_no_public_link(self):
        self.form.access = AdmissionForm.Access.VOUCHER
        self.form.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_hidden_department_and_honeypot_are_refused(self):
        self.assertEqual(self.post(self.hidden.pk).status_code, 400)
        self.assertEqual(self.post(self.nord.pk, website="spam").status_code, 400)
        self.assertFalse(Application.objects.exists())

    def test_application_lands_in_the_chosen_department_and_fills_extra_fields(self):
        response = self.post(self.nord.pk)
        self.assertEqual(response.status_code, 201, response.content)
        application = Application.objects.get()
        self.assertEqual(application.department, self.nord)
        self.assertIsNone(application.voucher)

        decisions.record_decision(application, outcome="approved", decided_on=timezone.localdate())
        member = take_over(application)
        self.assertEqual(member.extra_fields, {"schule": "Realschule"})
        self.assertEqual(list(member.departments.all()), [self.nord])

    def test_vouchers_still_work_for_public_forms(self):
        _, code = vouchers.create_voucher(self.form, department_id=self.mitte.pk)
        response = self.client.post(
            PUBLIC, {"answers": child_answers(schule="Realschule")}, format="json", HTTP_X_ADMISSION_CODE=code
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Application.objects.get().department, self.mitte)


PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@override_settings(MEDIA_ROOT=MEDIA)
class AttachmentTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.mitte = Department.objects.create(name="Mitte", code="at-mitte")
        publish_privacy_text()
        self.form = form_service.create_form(department=self.mitte, title="Aufnahme")
        schema = self.form.draft_schema
        schema["pages"][0]["sections"][0]["elements"].append(
            {"id": "e_attest", "type": "attachment", "key": "attest", "label": "Ärztliches Attest", "required": True}
        )
        form_service.save_draft(self.form, schema)
        form_service.publish(self.form)
        _, self.code = vouchers.create_voucher(self.form)

    def post(self, files):
        from django.core.files.uploadedfile import SimpleUploadedFile

        body = {"payload": json.dumps({"answers": child_answers()})}
        for key, (name, data) in files.items():
            body[f"file:{key}"] = SimpleUploadedFile(name, data, content_type="application/pdf")
        return self.client.post(PUBLIC, body, format="multipart", HTTP_X_ADMISSION_CODE=self.code)

    def test_required_attachment_must_be_sent(self):
        response = self.client.post(
            PUBLIC, {"answers": child_answers()}, format="json", HTTP_X_ADMISSION_CODE=self.code
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("attest", response.json()["answers"])

    def test_only_real_pdfs_are_accepted(self):
        for name, data in (("attest.png", PDF), ("attest.pdf", b"not a pdf")):
            response = self.post({"attest": (name, data)})
            self.assertEqual(response.status_code, 400, name)
        self.assertFalse(Application.objects.exists())

    def test_too_large_pdf_is_refused(self):
        response = self.post({"attest": ("attest.pdf", PDF + b"0" * (5 * 1024 * 1024))})
        self.assertEqual(response.status_code, 400)

    def test_pdf_is_sealed_and_becomes_a_member_attachment(self):
        response = self.post({"attest": ("Attest Mia.pdf", PDF)})
        self.assertEqual(response.status_code, 201, response.content)
        application = Application.objects.get()
        self.assertEqual(application.answers["attest"], {"file": "attest", "name": "Attest Mia.pdf"})
        self.assertEqual(application.files.get(key="attest").kind, "attachment")

        decisions.record_decision(application, outcome="approved", decided_on=timezone.localdate())
        member = take_over(application)
        attachment = member.attachments.get()
        self.assertEqual(attachment.name, "Attest Mia.pdf")
        self.assertEqual(attachment.mime_type, "application/pdf")
