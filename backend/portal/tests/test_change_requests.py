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


class PortalApiTests(TestCase):
    """PORTAL-03.2: a portal account requests changes only for people it may act for."""

    url = "/api/v1/portal/change-requests/"

    @classmethod
    def setUpTestData(cls):
        from portal.models import AccountLink

        cls.parent = Parent.objects.create(name="Sandra", lastname="Becker", email="s@example.invalid")
        cls.child = Member.objects.create(name="Mia", lastname="Becker", city="Bonn")
        cls.parent.children.add(cls.child)
        cls.stranger = Member.objects.create(name="Fremd", lastname="Kind")
        cls.user = User.objects.create_user("sandra", password="x", account_kind="portal")
        AccountLink.objects.create(user=cls.user, parent=cls.parent, status="confirmed")

    def setUp(self):
        self.client.force_login(self.user)

    def post(self, target, fields):
        return self.client.post(self.url, {"target": target, "fields": fields}, content_type="application/json")

    def test_submit_for_child_then_update(self):
        first = self.post({"kind": "member", "id": self.child.pk}, {"city": "Köln"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["fields"], [{"field": "city", "label": "Ort", "old": "Bonn", "new": "Köln"}])
        second = self.post({"kind": "member", "id": self.child.pk}, {"city": "Siegburg"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["version"], 2)
        listed = self.client.get(self.url).json()["results"]
        self.assertEqual([(r["kind"], r["status"]) for r in listed], [("member", "open")])
        self.assertNotIn("current", listed[0]["fields"][0])  # reviewers only

    def test_own_parent_record_with_second_email(self):
        response = self.post({"kind": "parent"}, {"email2": "zwei@example.invalid"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["kind"], "parent")

    def test_foreign_people_look_missing(self):
        self.assertEqual(self.post({"kind": "member", "id": self.stranger.pk}, {"city": "X"}).status_code, 404)
        self.assertEqual(self.post({"kind": "member", "id": 999999}, {"city": "X"}).status_code, 404)
        self.assertEqual(self.post("parent", {"city": "X"}).status_code, 404)

    def test_errors_per_field(self):
        response = self.post({"kind": "member", "id": self.child.pk}, {"email": "kaputt", "birthday": "2000-01-01"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["fields"]), {"birthday"})  # unknown fields are refused first
        response = self.post({"kind": "member", "id": self.child.pk}, {"email": "kaputt"})
        self.assertEqual(set(response.json()["fields"]), {"email"})

    def test_withdraw_only_own_requests(self):
        mine = self.post({"kind": "member", "id": self.child.pk}, {"city": "Köln"}).json()
        foreign = ChangeRequest.objects.create(target_member=self.stranger, fields=[])
        self.assertEqual(self.client.post(f"{self.url}{foreign.pk}/withdraw/").status_code, 404)
        response = self.client.post(f"{self.url}{mine['id']}/withdraw/")
        self.assertEqual(response.json()["status"], "withdrawn")
        self.assertEqual(self.client.post(f"{self.url}{mine['id']}/withdraw/").status_code, 409)

    def test_staff_accounts_cannot_use_the_portal_endpoint(self):
        staff = User.objects.create_user("leitung", password="x")
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)
