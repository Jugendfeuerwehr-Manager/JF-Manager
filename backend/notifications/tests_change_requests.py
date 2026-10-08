"""PORTAL-03.4: change requests reach reviewers and requesters; quick actions cr_review/cr_apply."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent
from notifications.dispatch import deliver_emails
from notifications.models import EmailDelivery, InboxItem
from portal import change_requests as cr
from portal.models import AccountLink

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ChangeRequestNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        mitte = Department.objects.create(name="Mitte")
        nord = Department.objects.create(name="Nord")
        reviewers = Group.objects.create(name="Prüfung")
        reviewers.permissions.add(Permission.objects.get(codename="review_changerequest"))
        cls.reviewer = User.objects.create_user("pruefer", email="p@example.invalid", password="x", first_name="Pia")
        UserDepartmentRole.objects.create(user=cls.reviewer, department=mitte).groups.add(reviewers)
        cls.outsider = User.objects.create_user("nord", email="n@example.invalid", password="x")
        UserDepartmentRole.objects.create(user=cls.outsider, department=nord).groups.add(reviewers)
        cls.child = Member.objects.create(name="Mia", lastname="Becker", mobile="0151 1")
        cls.child.departments.add(mitte)
        parent = Parent.objects.create(name="Sandra", lastname="Becker")
        parent.children.add(cls.child)
        cls.parent_user = User.objects.create_user(
            "sandra@example.invalid", email="sandra@example.invalid", password="x", account_kind="portal"
        )
        AccountLink.objects.create(user=cls.parent_user, parent=parent, status="confirmed")

    def submit(self, **fields):
        with self.captureOnCommitCallbacks(execute=True):
            return cr.submit(self.child, fields or {"mobile": "0170 2"}, self.parent_user)[0]

    def links(self, body):
        return re.findall(r"/a/([\w:.-]+)", body)

    def resolve(self, user, token, execute=False, url="resolve"):
        client = APIClient()
        client.force_authenticate(user)
        return client.post(f"/api/v1/actions/{'execute' if execute else url}/", {"token": token}, format="json")

    def test_submission_creates_one_task_and_a_mail_per_version(self):
        change = self.submit()
        task = InboxItem.objects.get(kind="cr_submitted")
        self.assertEqual(task.item_type, "task")
        self.assertEqual(task.title, "Änderungsantrag für Mia Becker")  # no requested values in titles
        self.assertEqual(list(task.recipients.values_list("user__username", flat=True)), ["pruefer"])
        self.submit(mobile="0170 3")
        self.assertEqual(InboxItem.objects.filter(kind="cr_submitted").count(), 1)
        self.assertEqual(EmailDelivery.objects.filter(kind="cr_submitted").count(), 2)
        deliver_emails()
        self.assertEqual(mail.outbox[-1].to, ["p@example.invalid"])
        self.assertIn("0170 3", mail.outbox[-1].body)
        self.assertIn("Alle übernehmen", mail.outbox[-1].body)
        self.assertEqual(change.pk, cr.open_request(self.child).pk)

    def test_decision_closes_the_task_and_informs_the_requester(self):
        change = self.submit()
        with self.captureOnCommitCallbacks(execute=True):
            cr.decide(change, self.reviewer, {"mobile": "reject"}, version=1, note="Bitte Nummer prüfen")
        self.assertEqual(InboxItem.objects.get(kind="cr_submitted").task_state, "done")
        notice = InboxItem.objects.get(kind="cr_decided")
        self.assertTrue(notice.recipients.filter(user=self.parent_user).exists())
        self.assertIn("abgelehnt", notice.title)
        deliver_emails()
        body = mail.outbox[-1].body
        self.assertEqual(mail.outbox[-1].to, ["sandra@example.invalid"])
        self.assertIn("Bitte Nummer prüfen", body)
        self.assertIn("Daten ansehen", body)

    def test_withdrawal_closes_the_task_without_mail_to_the_requester(self):
        change = self.submit()
        with self.captureOnCommitCallbacks(execute=True):
            cr.withdraw(change)
        self.assertEqual(InboxItem.objects.get(kind="cr_submitted").task_state, "done")
        self.assertFalse(InboxItem.objects.filter(kind="cr_decided").exists())

    def test_apply_link_from_the_mail(self):
        self.submit()
        deliver_emails()
        replies = [(self.resolve(self.reviewer, t).json(), t) for t in self.links(mail.outbox[-1].body)]
        self.assertTrue(all("action" in r for r, _ in replies), [r for r, _ in replies])
        tokens = {r["action"]: t for r, t in replies}
        self.assertLessEqual({"cr_review", "cr_apply"}, set(tokens))
        review = self.resolve(self.reviewer, tokens["cr_review"]).json()
        self.assertTrue(review["target_route"].startswith("/portal-verwaltung?tab=antraege"))
        preview = self.resolve(self.reviewer, tokens["cr_apply"]).json()
        self.assertEqual(preview["state"], "ready")
        self.assertIn("Mobil: 0151 1 → 0170 2", preview["lines"])
        self.assertEqual(self.resolve(self.outsider, tokens["cr_apply"]).status_code, 403)  # other account
        with self.captureOnCommitCallbacks(execute=True):
            done = self.resolve(self.reviewer, tokens["cr_apply"], execute=True).json()
        self.assertEqual(done["state"], "done")
        self.child.refresh_from_db()
        self.assertEqual(self.child.mobile, "0170 2")
        again = self.resolve(self.reviewer, tokens["cr_apply"]).json()
        self.assertEqual(again["state"], "done")

    def test_outdated_or_conflicting_link_sends_the_reviewer_to_the_review(self):
        self.submit()
        deliver_emails()
        first = [
            t for t in self.links(mail.outbox[-1].body) if self.resolve(self.reviewer, t).json()["action"] == "cr_apply"
        ]
        self.submit(mobile="0170 3")  # version 2
        outdated = self.resolve(self.reviewer, first[0], execute=True).json()
        self.assertEqual(outdated["state"], "not_available")
        self.child.refresh_from_db()
        self.assertEqual(self.child.mobile, "0151 1")
