"""PORTAL-03.1: change request model, validation and one open request per target."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from members.models import Member, Parent
from portal import change_requests as cr
from portal.models import ChangeRequest

User = get_user_model()


class ValidationTests(TestCase):
    def test_html_and_control_characters_are_removed(self):
        cleaned = cr.validate("member", {"city": "<b>Bonn</b>\u0000​  Nord\n", "street": "<script>x</script>Weg 1"})
        self.assertEqual(cleaned["city"], "Bonn Nord")
        self.assertEqual(cleaned["street"], "xWeg 1")

    def test_formula_prefixes_stay_plain_text(self):
        self.assertEqual(cr.validate("member", {"city": "=HYPERLINK(1)"})["city"], "=HYPERLINK(1)")

    def test_formats_and_lengths(self):
        cases = {
            "email": "keine-mail",
            "phone": "0228 abc",
            "zip_code": "1",
            "city": "x" * 201,
            "name": "  ",
        }
        with self.assertRaises(cr.ChangeRequestError) as caught:
            cr.validate("member", cases)
        self.assertEqual(set(caught.exception.fields), set(cases))

    def test_valid_values_pass(self):
        values = {"email": "a@example.invalid", "phone": "+49 228/123-4", "zip_code": "53111", "mobile": ""}
        self.assertEqual(cr.validate("member", values), values)

    def test_only_name_and_contact_fields(self):
        with self.assertRaises(cr.ChangeRequestError) as caught:
            cr.validate("member", {"birthday": "2000-01-01", "email2": "a@example.invalid"})
        self.assertEqual(set(caught.exception.fields), {"birthday", "email2"})
        self.assertEqual(cr.validate("parent", {"email2": "b@example.invalid"}), {"email2": "b@example.invalid"})

    def test_non_text_values_are_rejected(self):
        with self.assertRaises(cr.ChangeRequestError):
            cr.validate("member", {"city": ["Bonn"]})


class SubmitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = Member.objects.create(name="Mia", lastname="Becker", city="Bonn", email="mia@example.invalid")
        cls.parent = Parent.objects.create(name="Sandra", lastname="Becker", email="s@example.invalid")
        cls.user = User.objects.create_user("sandra", password="x", account_kind="portal")

    def test_submit_stores_old_and_new_and_changes_nothing(self):
        request, created = cr.submit(self.member, {"city": "Köln", "email": "mia@example.invalid"}, self.user)
        self.assertTrue(created)
        self.assertEqual(request.fields, [{"field": "city", "old": "Bonn", "new": "Köln"}])
        self.member.refresh_from_db()
        self.assertEqual(self.member.city, "Bonn")  # E2: nothing before approval

    def test_resubmit_updates_the_open_request(self):
        first, _ = cr.submit(self.member, {"city": "Köln"}, self.user)
        second, created = cr.submit(self.member, {"city": "Bonn", "phone": "0228 1"}, self.user)
        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.version, 2)
        self.assertEqual([e["field"] for e in second.fields], ["phone"])
        self.assertEqual(ChangeRequest.objects.count(), 1)

    def test_unchanged_values_are_refused(self):
        with self.assertRaises(cr.ChangeRequestError) as caught:
            cr.submit(self.member, {"city": " Bonn "}, self.user)
        self.assertEqual(caught.exception.code, "unchanged")

    def test_withdraw_then_a_new_request_is_possible(self):
        first, _ = cr.submit(self.parent, {"email2": "zwei@example.invalid"}, self.user)
        cr.withdraw(first)
        with self.assertRaises(cr.ChangeRequestError):
            cr.withdraw(first)
        second, created = cr.submit(self.parent, {"email2": "zwei@example.invalid"}, self.user)
        self.assertTrue(created)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(cr.open_request(self.parent), second)

    def test_database_allows_one_open_request_and_one_target(self):
        ChangeRequest.objects.create(target_member=self.member, fields=[])
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChangeRequest.objects.create(target_member=self.member, fields=[])
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChangeRequest.objects.create(target_member=self.member, target_parent=self.parent, fields=[])
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChangeRequest.objects.create(fields=[])
        ChangeRequest.objects.create(target_member=self.member, fields=[], status="applied")

    def test_payload_marks_conflicts_against_the_current_value(self):
        request, _ = cr.submit(self.member, {"city": "Köln", "phone": "1"}, self.user)
        Member.objects.filter(pk=self.member.pk).update(city="Siegburg")
        rows = {r["field"]: r for r in cr.payload(request, with_current=True)["fields"]}
        self.assertTrue(rows["city"]["conflict"])
        self.assertEqual(rows["city"]["current"], "Siegburg")
        self.assertFalse(rows["phone"]["conflict"])
        self.assertEqual(rows["city"]["label"], "Ort")
