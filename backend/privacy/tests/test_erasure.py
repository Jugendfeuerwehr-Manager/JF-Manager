"""DSGVO: former members are anonymized or erased without personal traces. Fictional data."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import EmailMessage, EmailRecipient, Event, EventType, Member, Parent
from notifications.models import InboxItem
from portal.models import ChangeLog
from privacy.models import ConsentRecord
from privacy.services.erasure import anonymize_member, erase_member
from privacy.services.retention import purge_personal_data
from qualifications.models import Qualification, QualificationType

User = get_user_model()


def role(user, department, *codenames):
    group = Group.objects.create(name=f"{user.username}-{department.code}")
    group.permissions.add(*Permission.objects.filter(codename__in=codenames))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class ErasureTestBase(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Mitte", code="erasure-mitte")
        self.member = Member.objects.create(
            name="Mia",
            lastname="Muster",
            gender="female",
            birthday=date(2012, 5, 17),
            email="mia@example.invalid",
            street="Musterweg 1",
            city="Musterstadt",
            phone="0123",
            notes="Allergie: Wespenstich",
            identityCardNumber="JF-42",
            joined=date(2020, 1, 1),
        )
        self.member.departments.add(self.department)
        self.only_parent = Parent.objects.create(name="Eva", lastname="Muster", email="eva@example.invalid")
        self.only_parent.children.add(self.member)
        sibling = Member.objects.create(name="Ben", lastname="Muster")
        self.shared_parent = Parent.objects.create(name="Tom", lastname="Muster")
        self.shared_parent.children.add(self.member, sibling)
        self.sender = User.objects.create_user("leitung", password="x")
        message = EmailMessage.objects.create(sender=self.sender, subject="Elternabend", body_html="", status="sent")
        EmailRecipient.objects.create(
            email_message=message,
            member=self.member,
            email_address="mia@example.invalid",
            recipient_name="Mia Muster",
            personalized_body_html="<p>Hallo Mia</p>",
        )
        ChangeLog.objects.create(
            target_kind="member", target_id=self.member.pk, field="street", old="Altweg", new="Musterweg 1"
        )
        InboxItem.objects.create(
            kind="x",
            category="requests",
            item_type="notice",
            title="Mia Muster hat Daten geändert",
            object_type="members.member",
            object_id=self.member.pk,
        )
        ConsentRecord.objects.create(member=self.member, kind="photo_public", status="granted", source="staff")
        Event.objects.create(
            member=self.member,
            type=EventType.objects.create(name="Notiz"),
            datetime=date(2024, 3, 1),
            notes="Gespräch mit Eltern",
        )
        self.qualification = Qualification.objects.create(
            member=self.member,
            type=QualificationType.objects.create(name="Leistungsspange"),
            date_acquired=date(2023, 6, 1),
            note="Prüfer Herr X",
        )

    def assert_no_personal_traces(self):
        self.assertFalse(EmailRecipient.objects.filter(email_address="mia@example.invalid").exists())
        self.assertFalse(EmailRecipient.objects.filter(recipient_name__contains="Mia").exists())
        self.assertFalse(ChangeLog.objects.filter(target_kind="member", target_id=self.member.pk).exists())
        self.assertFalse(InboxItem.objects.filter(title__contains="Mia").exists())
        self.assertFalse(ConsentRecord.objects.filter(member_id=self.member.pk).exists())
        self.assertFalse(Parent.objects.filter(pk=self.only_parent.pk).exists())
        self.shared_parent.refresh_from_db()
        self.assertEqual(self.shared_parent.children.count(), 1)


class AnonymizeTests(ErasureTestBase):
    def test_anonymize_keeps_statistics_and_removes_identity(self):
        anonymize_member(self.member)
        member = Member.objects.get(pk=self.member.pk)
        self.assertEqual((member.name, member.lastname), ("Ehemaliges", f"Mitglied #{member.pk}"))
        for field in ("email", "street", "city", "phone", "notes", "identityCardNumber"):
            self.assertEqual(getattr(member, field), "", field)
        self.assertEqual(member.birthday, date(2012, 1, 1))
        self.assertEqual((member.gender, member.joined), ("female", date(2020, 1, 1)))
        self.assertEqual(member.left_at, timezone.localdate())
        self.assertIsNotNone(member.anonymized_at)
        self.assertEqual(list(member.departments.all()), [self.department])
        self.assertFalse(Event.objects.filter(member=member).exists())
        self.qualification.refresh_from_db()
        self.assertEqual(self.qualification.note, "")  # the qualification itself stays
        self.assert_no_personal_traces()

    def test_anonymize_twice_is_refused(self):
        anonymize_member(self.member)
        from privacy.services.erasure import ErasureError

        with self.assertRaises(ErasureError):
            anonymize_member(self.member)


class EraseTests(ErasureTestBase):
    def test_erase_leaves_no_traces(self):
        erase_member(self.member)
        self.assertFalse(Member.objects.filter(pk=self.member.pk).exists())
        self.assert_no_personal_traces()


class AutomaticAnonymizationTests(ErasureTestBase):
    def test_former_members_are_announced_then_anonymized(self):
        leader = User.objects.create_user("jugendwart", password="x")
        role(leader, self.department, "anonymize_member")
        Member.objects.filter(pk=self.member.pk).update(left_at=timezone.localdate() - timedelta(days=340))
        purge_personal_data()
        task = InboxItem.objects.get(kind="privacy_anonymize_due")
        self.assertEqual(task.item_type, "task")
        self.assertTrue(task.recipients.filter(user=leader).exists())
        self.assertIsNone(Member.objects.get(pk=self.member.pk).anonymized_at)
        purge_personal_data()  # announced only once
        self.assertEqual(InboxItem.objects.filter(kind="privacy_anonymize_due").count(), 1)

        Member.objects.filter(pk=self.member.pk).update(left_at=timezone.localdate() - timedelta(days=366))
        results = {result.name: result.count for result in purge_personal_data()}
        self.assertEqual(results["member_anonymize_after_days"], 1)
        self.assertIsNotNone(Member.objects.get(pk=self.member.pk).anonymized_at)
        task.refresh_from_db()
        self.assertEqual(task.task_state, "done")

    def test_members_without_leave_date_are_never_touched(self):
        purge_personal_data()
        self.assertIsNone(Member.objects.get(pk=self.member.pk).anonymized_at)


class AnonymizeApiTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="api-mitte")
        self.nord = Department.objects.create(name="Nord", code="api-nord")
        self.member = Member.objects.create(name="Mia", lastname="Muster")
        self.member.departments.add(self.mitte)
        self.url = f"/api/v1/members/{self.member.pk}/anonymize/"

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.post(self.url).status_code, (401, 403))

    def test_editor_without_anonymize_right_is_refused(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_member", "change_member"))
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertIsNone(Member.objects.get(pk=self.member.pk).anonymized_at)

    def test_foreign_department_cannot_reach_the_member(self):
        self.client.force_authenticate(self.user("nord", self.nord, "view_member", "anonymize_member"))
        self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_right_holder_anonymizes_and_list_hides_the_row(self):
        user = self.user("jugendwart", self.mitte, "view_member", "anonymize_member")
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["name"], "Ehemaliges")
        self.assertEqual(self.client.post(self.url).status_code, 409)
        listed = {row["id"] for row in self.client.get("/api/v1/members/").json()["results"]}
        self.assertNotIn(self.member.pk, listed)
        listed = {row["id"] for row in self.client.get("/api/v1/members/?include_anonymized=true").json()["results"]}
        self.assertIn(self.member.pk, listed)

    def test_leave_date_is_saved_and_can_be_cleared(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_member", "change_member"))
        url = f"/api/v1/members/{self.member.pk}/"
        self.assertEqual(self.client.patch(url, {"left_at": "2026-09-30"}, format="multipart").status_code, 200)
        self.assertEqual(Member.objects.get(pk=self.member.pk).left_at, date(2026, 9, 30))
        self.assertEqual(self.client.patch(url, {"left_at": ""}, format="multipart").status_code, 200)
        self.assertIsNone(Member.objects.get(pk=self.member.pk).left_at)

    def test_delete_uses_the_erasure_service(self):
        ChangeLog.objects.create(target_kind="member", target_id=self.member.pk, field="city", old="A", new="B")
        self.client.force_authenticate(self.user("admin", self.mitte, "view_member", "delete_member"))
        self.assertEqual(self.client.delete(f"/api/v1/members/{self.member.pk}/").status_code, 204)
        self.assertFalse(ChangeLog.objects.filter(target_kind="member", target_id=self.member.pk).exists())
