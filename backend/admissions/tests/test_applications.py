"""Vouchers, public submission, seals, committee decisions and takeover. Fictional data."""

import base64
import io
import shutil
import tempfile
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from admissions.models import AdmissionVoucher, Application, Seal
from admissions.services import decisions, takeover, vouchers
from admissions.services import forms as form_service
from admissions.services.submission import submit
from admissions.services.verification import verify_application, verify_public
from admissions.services.vouchers import VoucherError
from admissions.tests.test_forms import publish_privacy_text
from departments.models import Department
from members.models import ExportAudit, Member, Parent, Status
from membership.models import MembershipEvent
from membership.tests.test_lifecycle import role
from privacy.models import ConsentRecord

User = get_user_model()
PUBLIC = "/api/v1/public/admissions/"
MEDIA = tempfile.mkdtemp(prefix="admissions-test-")


def png_data_url(size=(40, 20), fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format=fmt)
    mime = "png" if fmt == "PNG" else "jpeg"
    return f"data:image/{mime};base64,{base64.b64encode(buffer.getvalue()).decode()}"


def child_answers(**overrides):
    answers = {
        "vorname": "Mia",
        "nachname": "Muster",
        "geburtsdatum": (date.today() - timedelta(days=12 * 365)).isoformat(),
        "geschlecht": "female",
        "strasse": "Musterweg 1",
        "plz": "12345",
        "ort": "Musterstadt",
        "email": "mia@example.invalid",
        "sorgeberechtigte": [
            {"name": "Eva", "lastname": "Muster", "mobile": "0170 000000", "email": "eva@example.invalid"}
        ],
        "schwimmer": True,
        "datenschutz": True,
        "einwilligung_daten": True,
        "einwilligung_daten_eltern": True,
        "fotos_intern": True,
        "fotos_oeffentlich": False,
        "verpflichtung": True,
        "passbild": png_data_url((300, 400), "JPEG"),
        "unterschrift_antragsteller": png_data_url(),
        "unterschrift_sorgeberechtigte_1": png_data_url(),
    }
    answers.update(overrides)
    return answers


@override_settings(MEDIA_ROOT=MEDIA)
class AdmissionTestBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.department = Department.objects.create(name="Mitte", code="adm-mitte")
        self.trial = Status.objects.create(name="Anwärter", category=Status.Category.TRIAL)
        self.form = form_service.create_form(department=self.department, title="Aufnahmeantrag")
        self.form.initial_status = self.trial
        self.form.save()
        publish_privacy_text()
        self.version = form_service.publish(self.form)
        self.voucher, self.code = vouchers.create_voucher(self.form, label="Mia", prefill={"vorname": "Mia"})

    def approved(self):
        application, _ = submit(self.code, child_answers())
        decisions.record_decision(application, outcome="approved", decided_on=timezone.localdate())
        application.refresh_from_db()
        return application


class VoucherTests(AdmissionTestBase):
    def test_code_is_readable_and_only_its_hash_is_stored(self):
        self.assertRegex(self.code, r"^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")
        self.assertNotIn(self.code.replace("-", ""), str(AdmissionVoucher.objects.values().get()))
        self.assertEqual(vouchers.open_voucher(self.code.lower().replace("-", " ")), self.voucher)

    def test_unpublished_or_inactive_forms_get_no_vouchers(self):
        draft = form_service.create_form(department=self.department, title="Entwurf")
        with self.assertRaises(ValidationError):
            vouchers.create_voucher(draft)
        self.form.is_active = False
        with self.assertRaises(ValidationError):
            vouchers.create_voucher(self.form)

    def test_revoked_and_expired_codes_are_unusable(self):
        vouchers.revoke(self.voucher)
        with self.assertRaises(VoucherError):
            vouchers.open_voucher(self.code)
        other, code = vouchers.create_voucher(self.form)
        AdmissionVoucher.objects.filter(pk=other.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(VoucherError):
            vouchers.open_voucher(code)


class SubmissionTests(AdmissionTestBase):
    def test_submission_stores_answers_files_and_seals_them(self):
        application, seal = submit(self.code, child_answers())
        self.assertEqual(application.applicant_name, "Mia Muster")
        self.assertEqual(application.answers["passbild"], {"file": "passbild"})
        self.assertEqual(
            set(application.files.values_list("key", flat=True)),
            {"passbild", "unterschrift_antragsteller", "unterschrift_sorgeberechtigte_1"},
        )
        self.assertEqual(seal.kind, Seal.Kind.SUBMISSION)
        self.assertTrue(verify_application(application)["valid"])
        self.voucher.refresh_from_db()
        self.assertIsNotNone(self.voucher.used_at)

    def test_a_code_works_only_once(self):
        submit(self.code, child_answers())
        with self.assertRaises(VoucherError):
            submit(self.code, child_answers())

    def test_missing_required_answers_are_reported_per_field(self):
        with self.assertRaises(Exception) as caught:
            submit(self.code, child_answers(datenschutz=False, sorgeberechtigte=[], unterschrift_antragsteller=""))
        errors = caught.exception.detail["answers"]
        self.assertEqual(set(errors), {"datenschutz", "sorgeberechtigte", "unterschrift_antragsteller"})
        self.assertFalse(Application.objects.exists())

    def test_adults_need_no_guardians(self):
        adult = child_answers(
            geburtsdatum="1990-01-01",
            sorgeberechtigte=[],
            einwilligung_daten_eltern=False,
            unterschrift_sorgeberechtigte_1="",
        )
        application, _ = submit(self.code, adult)
        self.assertNotIn("sorgeberechtigte", application.answers)

    def test_broken_images_and_bad_choices_are_rejected(self):
        with self.assertRaises(Exception) as caught:
            submit(self.code, child_answers(passbild="data:image/png;base64,AAAA", geschlecht="x"))
        self.assertEqual(set(caught.exception.detail["answers"]), {"passbild", "geschlecht"})

    def test_tampering_breaks_the_seal(self):
        application, _ = submit(self.code, child_answers())
        Application.objects.filter(pk=application.pk).update(applicant_name="Jemand anderes")
        application.refresh_from_db()
        self.assertFalse(verify_application(application)["valid"])

    def test_sealed_content_cannot_be_saved_and_seals_cannot_change(self):
        application, seal = submit(self.code, child_answers())
        application.answers = {**application.answers, "vorname": "Max"}
        with self.assertRaises(DjangoValidationError):
            application.save()
        seal.content_hash = "0" * 64
        with self.assertRaises(DjangoValidationError):
            seal.save()


class DecisionAndTakeoverTests(AdmissionTestBase):
    def test_decision_is_sealed_in_the_chain(self):
        application, _ = submit(self.code, child_answers())
        decisions.record_decision(application, outcome="approved", decided_on=timezone.localdate(), votes=(5, 0, 1))
        result = verify_application(application)
        self.assertTrue(result["valid"])
        self.assertEqual([s["kind"] for s in result["seals"]], ["submission", "decision"])

    def test_a_decided_application_cannot_be_decided_again_unless_deferred(self):
        application, _ = submit(self.code, child_answers())
        decisions.record_decision(application, outcome="deferred", decided_on=timezone.localdate())
        decisions.record_decision(application, outcome="approved", decided_on=timezone.localdate())
        with self.assertRaises(ValidationError):
            decisions.record_decision(application, outcome="rejected", decided_on=timezone.localdate())

    def test_takeover_creates_member_guardian_consents_and_join(self):
        application = self.approved()
        member = takeover.take_over(application, joined=date(2026, 11, 1))
        self.assertEqual((member.name, member.lastname, member.gender), ("Mia", "Muster", "female"))
        self.assertEqual((member.status, member.joined, member.canSwimm), (self.trial, date(2026, 11, 1), True))
        self.assertTrue(member.avatar)
        self.assertEqual(list(member.departments.all()), [self.department])
        parent = Parent.objects.get(children=member)
        self.assertEqual((parent.name, parent.email), ("Eva", "eva@example.invalid"))
        self.assertTrue(
            MembershipEvent.objects.filter(member=member, kind="joined_new", date=date(2026, 11, 1)).exists()
        )
        member_kinds = set(ConsentRecord.objects.filter(member=member).values_list("kind", flat=True))
        self.assertEqual(member_kinds, {"privacy_notice_ack", "data_processing_applicant", "photo_internal"})
        parent_consent = ConsentRecord.objects.get(parent=parent, kind="data_processing_guardian")
        self.assertEqual(parent_consent.source, "application")
        self.assertIn(
            "Verwaltungszwecken",
            ConsentRecord.objects.get(member=member, kind="data_processing_applicant").text_snapshot,
        )
        application.refresh_from_db()
        self.assertEqual((application.status, application.member), (Application.Status.TAKEN_OVER, member))

    def test_takeover_links_an_existing_parent(self):
        sibling = Member.objects.create(name="Ben", lastname="Muster")
        sibling.departments.add(self.department)
        existing = Parent.objects.create(name="Eva", lastname="Muster", email="eva@example.invalid")
        existing.children.add(sibling)
        application = self.approved()
        self.assertEqual(takeover.parent_suggestions(application)[0][0]["id"], existing.pk)
        member = takeover.take_over(application, parent_links={"0": existing.pk})
        self.assertEqual(list(Parent.objects.filter(children=member)), [existing])

    def test_only_approved_applications_are_taken_over(self):
        application, _ = submit(self.code, child_answers())
        with self.assertRaises(ValidationError):
            takeover.take_over(application)
        self.assertFalse(Member.objects.exists())

    def test_public_check_reveals_no_personal_data(self):
        _, seal = submit(self.code, child_answers())
        result = verify_public(seal.public_id)
        self.assertTrue(result["valid"])
        self.assertNotIn("Mia", str(result))


@override_settings(MEDIA_ROOT=MEDIA)
class PublicApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.department = Department.objects.create(name="Mitte", code="adp-mitte")
        self.form = form_service.create_form(department=self.department, title="Aufnahmeantrag")
        publish_privacy_text()
        form_service.publish(self.form)
        self.voucher, self.code = vouchers.create_voucher(self.form, prefill={"vorname": "Mia"})

    def test_form_is_shown_for_a_valid_code_from_the_header(self):
        response = self.client.get(PUBLIC, HTTP_X_ADMISSION_CODE=self.code)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["prefill"], {"vorname": "Mia"})
        self.assertEqual(response.json()["department"], "Mitte")

    def test_invalid_used_and_revoked_codes_look_the_same(self):
        bodies = [self.client.get(PUBLIC, HTTP_X_ADMISSION_CODE="AAAA-BBBB-CCCC").json()]
        submit(self.code, child_answers())
        bodies.append(self.client.get(PUBLIC, HTTP_X_ADMISSION_CODE=self.code).json())
        other, code = vouchers.create_voucher(self.form)
        vouchers.revoke(other)
        bodies.append(self.client.get(PUBLIC, HTTP_X_ADMISSION_CODE=code).json())
        self.assertEqual(len({str(body) for body in bodies}), 1)

    def test_submit_returns_the_seal_reference(self):
        response = self.client.post(
            PUBLIC, {"answers": child_answers()}, format="json", HTTP_X_ADMISSION_CODE=self.code
        )
        self.assertEqual(response.status_code, 201, response.content)
        public_id = response.json()["seal"]["public_id"]
        check = self.client.get(f"{PUBLIC}verify/{public_id}/")
        self.assertEqual(check.status_code, 200)
        self.assertTrue(check.json()["valid"])

    def test_guessing_is_throttled(self):
        statuses = [self.client.get(PUBLIC, HTTP_X_ADMISSION_CODE="AAAA-BBBB-CCCC").status_code for _ in range(12)]
        self.assertIn(429, statuses)


@override_settings(MEDIA_ROOT=MEDIA)
class StaffApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.mitte = Department.objects.create(name="Mitte", code="ads-mitte")
        self.nord = Department.objects.create(name="Nord", code="ads-nord")
        self.form = form_service.create_form(department=self.mitte, title="Aufnahmeantrag")
        publish_privacy_text()
        form_service.publish(self.form)
        _, code = vouchers.create_voucher(self.form)
        self.application, _ = submit(code, child_answers())

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def test_anonymous_is_rejected_everywhere(self):
        for url in ("/api/v1/admissions/applications/", "/api/v1/admissions/vouchers/", "/api/v1/admissions/meetings/"):
            self.assertIn(self.client.get(url).status_code, (401, 403), url)

    def test_missing_right_is_refused(self):
        self.client.force_authenticate(self.user("ohne", self.mitte, "view_member"))
        self.assertEqual(self.client.get("/api/v1/admissions/applications/").status_code, 403)

    def test_foreign_department_cannot_see_or_decide(self):
        self.client.force_authenticate(self.user("nord", self.nord, "view_application", "record_decision"))
        self.assertEqual(self.client.get("/api/v1/admissions/applications/").json()["count"], 0)
        response = self.client.post(
            f"/api/v1/admissions/applications/{self.application.pk}/decide/",
            {"outcome": "approved", "decided_on": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_reader_cannot_decide(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_application"))
        response = self.client.post(
            f"/api/v1/admissions/applications/{self.application.pk}/decide/",
            {"outcome": "approved", "decided_on": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_committee_decides_in_a_meeting_and_leader_takes_over(self):
        self.client.force_authenticate(
            self.user(
                "jugendwart",
                self.mitte,
                "view_application",
                "record_decision",
                "take_over_application",
                "add_member",
                "view_committeemeeting",
                "add_committeemeeting",
            )
        )
        meeting = self.client.post(
            "/api/v1/admissions/meetings/",
            {"department": self.mitte.pk, "body": "Jugendausschuss", "date": str(timezone.localdate())},
            format="json",
        ).json()
        response = self.client.post(
            f"/api/v1/admissions/meetings/{meeting['id']}/decide/",
            {"applications": [self.application.pk], "outcome": "approved", "votes_yes": 6},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        response = self.client.post(
            f"/api/v1/admissions/applications/{self.application.pk}/take-over/", {}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Member.objects.filter(pk=response.json()["member"], departments=self.mitte).exists())

    def test_voucher_code_is_returned_once(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_admissionvoucher", "add_admissionvoucher"))
        response = self.client.post(
            "/api/v1/admissions/vouchers/", {"form": self.form.pk, "vorname": "Ben"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIn("code", response.json())
        listed = self.client.get("/api/v1/admissions/vouchers/").json()["results"]
        self.assertTrue(all("code" not in row for row in listed))

    def test_voucher_for_foreign_department_is_refused(self):
        self.client.force_authenticate(self.user("nord", self.nord, "view_admissionvoucher", "add_admissionvoucher"))
        response = self.client.post("/api/v1/admissions/vouchers/", {"form": self.form.pk}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_export_is_sealed_and_audited(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_application", "export_application"))
        response = self.client.get(f"/api/v1/admissions/applications/{self.application.pk}/export/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("export_seal", response.json())
        self.assertTrue(ExportAudit.objects.filter(action="export", object_id=self.application.pk).exists())
        self.assertTrue(Seal.objects.filter(subject_id=self.application.pk, kind="export").exists())

    def test_export_needs_its_right(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_application"))
        response = self.client.get(f"/api/v1/admissions/applications/{self.application.pk}/export/")
        self.assertEqual(response.status_code, 403)
