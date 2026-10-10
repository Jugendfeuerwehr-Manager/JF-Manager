"""PORTAL-04.3: own area of linked staff accounts, self-change log and four-eyes lock (E14, Q4)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Group, Parent
from participation.models import Registration
from participation.tests.helpers import future_day, make_member, make_session
from portal.change_requests import submit
from portal.models import AccountLink, ChangeLog
from qualifications.models import Qualification, QualificationType, SpecialTask, SpecialTaskType

User = get_user_model()

RIGHTS = [
    ("members", "view_member"),
    ("members", "change_member"),
    ("members", "view_parent"),
    ("members", "change_parent"),
    ("qualifications", "view_qualification"),
    ("qualifications", "add_qualification"),
    ("qualifications", "change_qualification"),
    ("qualifications", "delete_qualification"),
    ("qualifications", "view_specialtask"),
    ("qualifications", "add_specialtask"),
    ("qualifications", "change_specialtask"),
    ("qualifications", "delete_specialtask"),
    ("portal", "review_changerequest"),
]


def leader_role(user, department):
    group, _ = AuthGroup.objects.get_or_create(name="Leitung")
    for app, codename in RIGHTS:
        group.permissions.add(Permission.objects.get(codename=codename, content_type__app_label=app))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class OwnAreaBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte", code="mitte")
        cls.group = Group.objects.create(name="Rot", department=cls.mitte)
        cls.leader = User.objects.create_user("leitung", first_name="Tobias", last_name="Lehmann")
        leader_role(cls.leader, cls.mitte)
        cls.colleague = User.objects.create_user("kollegin", first_name="Sabine", last_name="Hahn")
        leader_role(cls.colleague, cls.mitte)
        cls.own = make_member(cls.mitte, "Tobias", cls.group, birthday=date(1990, 5, 1))
        cls.child = make_member(cls.mitte, "Ella", cls.group, birthday=date(2014, 5, 1))
        cls.other = make_member(cls.mitte, "Fremd", cls.group, birthday=date(2013, 5, 1))
        cls.parent = Parent.objects.create(name="Tobias", lastname="Lehmann")
        cls.parent.children.add(cls.child)
        cls.link = AccountLink.objects.create(user=cls.leader, member=cls.own, parent=cls.parent, status="confirmed")
        cls.session = make_session(cls.mitte, day=future_day(20), groups=[cls.group])

    def setUp(self):
        cache.clear()

    def client_for(self, user, session=False):
        client = APIClient()
        if session:
            client.force_login(user)
        else:
            client.force_authenticate(user)
        return client


class OwnAreaTests(OwnAreaBase):
    def test_overview_lists_self_and_children_with_rights(self):
        data = self.client_for(self.leader).get("/api/v1/my/").data
        self.assertEqual(
            [(p["id"], p["relation"]) for p in data["people"]], [(self.own.pk, "self"), (self.child.pk, "child")]
        )
        self.assertEqual(data["can_edit"], {"member": True, "parent": True})
        self.assertIn("andere Person", data["evidence_notice"])

    def test_without_confirmed_link_the_area_is_closed(self):
        self.assertEqual(self.client_for(self.colleague).get("/api/v1/my/").status_code, 403)
        AccountLink.objects.filter(pk=self.link.pk).update(status="pending")
        self.assertEqual(self.client_for(self.leader).get("/api/v1/my/").status_code, 403)

    def test_portal_accounts_stay_out(self):
        portal = User.objects.create_user("p@example.invalid", account_kind="portal")
        AccountLink.objects.create(user=portal, member=self.other, status="confirmed")
        client = self.client_for(portal, session=True)
        for path in (
            "/api/v1/my/",
            f"/api/v1/my/sessions/?person={self.other.pk}",
            f"/api/v1/my/people/{self.other.pk}/",
        ):
            response = client.get(path)
            self.assertEqual(response.status_code, 403, path)
            self.assertEqual(response.json()["code"], "portal_account_forbidden")

    def test_own_data_show_every_category_and_account_qualifications(self):
        kind = QualificationType.objects.create(name="Juleica")
        Qualification.objects.create(type=kind, user=self.leader, date_acquired=date(2024, 1, 1))
        data = self.client_for(self.leader).get(f"/api/v1/my/people/{self.own.pk}/").data
        self.assertIn("special_tasks", data["categories"])
        self.assertIn("membership", data)
        self.assertEqual(data["account_qualifications"][0]["type"], "Juleica")
        self.assertEqual(self.client_for(self.leader).get(f"/api/v1/my/people/{self.other.pk}/").status_code, 404)
        child = self.client_for(self.leader).get(f"/api/v1/my/people/{self.child.pk}/").data
        self.assertEqual(child["relation"], "child")

    def test_register_and_cancel_oneself_and_own_child(self):
        client = self.client_for(self.leader)
        listing = client.get("/api/v1/my/sessions/", {"person": self.own.pk})
        self.assertEqual(listing.status_code, 200, listing.content)
        self.assertEqual(listing.data["sessions"][0]["id"], self.session.pk)
        for person in (self.own, self.child):
            url = f"/api/v1/my/sessions/{self.session.pk}/registrations/{person.pk}/"
            response = client.put(url, {"target": "cancelled", "reason_category": "urlaub"}, format="json")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.data["state"], "cancelled")
        registrations = Registration.objects.filter(session=self.session)
        self.assertEqual(
            {(r.member_id, r.source) for r in registrations},
            {(self.own.pk, "portal_member"), (self.child.pk, "portal_parent")},
        )
        url = f"/api/v1/my/sessions/{self.session.pk}/registrations/{self.other.pk}/"
        self.assertEqual(client.put(url, {"target": "cancelled"}, format="json").status_code, 404)

    def test_absence_preview_for_oneself(self):
        response = self.client_for(self.leader).post(
            "/api/v1/my/absences/preview/",
            {"person": self.own.pk, "from": str(future_day(1)), "to": str(future_day(30))},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["will_cancel"], 1)


class SelfChangeTests(OwnAreaBase):
    def test_own_member_change_is_logged_as_self_change(self):
        response = self.client_for(self.leader).patch(
            f"/api/v1/members/{self.own.pk}/", {"mobile": "0170 5550100", "notes": "geheim"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        rows = {row.field: row for row in ChangeLog.objects.filter(target_kind="member", target_id=self.own.pk)}
        self.assertEqual(set(rows), {"mobile", "notes"})
        self.assertTrue(rows["mobile"].self_change)
        self.assertEqual(rows["mobile"].new, "0170 5550100")
        self.assertEqual(rows["notes"].new, "(geändert)")  # free text never copied into the log
        log = self.client_for(self.colleague).get(f"/api/v1/members/{self.own.pk}/change-log/").data["results"]
        self.assertTrue(all(entry["self_change"] for entry in log))
        self.assertEqual(log[0]["applied_by"], "Tobias Lehmann")

    def test_own_child_and_parent_record_count_as_own(self):
        self.client_for(self.leader).patch(f"/api/v1/members/{self.child.pk}/", {"city": "Neustadt"}, format="json")
        self.client_for(self.leader).patch(f"/api/v1/parents/{self.parent.pk}/", {"mobile": "0170 1"}, format="json")
        self.assertTrue(
            ChangeLog.objects.filter(target_kind="member", target_id=self.child.pk, self_change=True).exists()
        )
        self.assertTrue(
            ChangeLog.objects.filter(target_kind="parent", target_id=self.parent.pk, self_change=True).exists()
        )

    def test_other_changes_are_not_marked(self):
        self.client_for(self.leader).patch(f"/api/v1/members/{self.other.pk}/", {"city": "Neustadt"}, format="json")
        self.client_for(self.colleague).patch(f"/api/v1/members/{self.own.pk}/", {"city": "Neustadt"}, format="json")
        self.assertFalse(ChangeLog.objects.exists())

    def test_change_log_needs_member_rights(self):
        outsider = User.objects.create_user("aussen")
        self.assertIn(
            self.client_for(outsider).get(f"/api/v1/members/{self.own.pk}/change-log/").status_code, (403, 404)
        )


class FourEyesTests(OwnAreaBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.kind = QualificationType.objects.create(name="Erste Hilfe")
        cls.task_type = SpecialTaskType.objects.create(name="Kassenwart")

    def create(self, actor, **target):
        return self.client_for(actor).post(
            "/api/v1/qualifications/", {"type": self.kind.pk, "date_acquired": "2025-01-01", **target}, format="json"
        )

    def assert_own_record(self, response):
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.data["code"], "own_record")
        self.assertIn("andere Person", response.data["detail"])

    def test_own_member_own_account_and_own_child_are_locked(self):
        self.assert_own_record(self.create(self.leader, member=self.own.pk))
        self.assert_own_record(self.create(self.leader, member=self.child.pk))
        self.assert_own_record(self.create(self.leader, user=self.leader.pk))
        self.assertEqual(self.create(self.leader, member=self.other.pk).status_code, 201)
        self.assertEqual(self.create(self.colleague, member=self.own.pk).status_code, 201)

    def test_existing_own_evidence_cannot_be_changed_or_deleted(self):
        own = Qualification.objects.create(type=self.kind, member=self.own, date_acquired=date(2024, 1, 1))
        client = self.client_for(self.leader)
        self.assert_own_record(
            client.patch(f"/api/v1/qualifications/{own.pk}/", {"date_acquired": "2024-02-01"}, format="json")
        )
        self.assert_own_record(client.delete(f"/api/v1/qualifications/{own.pk}/"))
        foreign = Qualification.objects.create(type=self.kind, member=self.other, date_acquired=date(2024, 1, 1))
        # Moving a foreign record onto oneself is refused as well.
        self.assert_own_record(
            client.patch(f"/api/v1/qualifications/{foreign.pk}/", {"member": self.own.pk}, format="json")
        )
        self.assertTrue(Qualification.objects.filter(pk=own.pk).exists())

    def test_special_tasks_are_locked(self):
        client = self.client_for(self.leader)
        response = client.post(
            "/api/v1/qualifications/specialtasks/",
            {"task": self.task_type.pk, "member": self.own.pk, "start_date": "2025-01-01"},
            format="json",
        )
        self.assert_own_record(response)
        task = SpecialTask.objects.create(task=self.task_type, member=self.own, start_date=date(2025, 1, 1))
        self.assert_own_record(client.post(f"/api/v1/qualifications/specialtasks/{task.pk}/end_task/"))
        self.assert_own_record(client.delete(f"/api/v1/qualifications/specialtasks/{task.pk}/"))

    def test_pending_link_already_locks(self):
        AccountLink.objects.filter(pk=self.link.pk).update(status="pending")
        self.assert_own_record(self.create(self.leader, member=self.own.pk))
        AccountLink.objects.filter(pk=self.link.pk).update(status="rejected")
        self.assertEqual(self.create(self.leader, member=self.own.pk).status_code, 201)

    def test_change_request_of_own_child_is_decided_by_someone_else(self):
        portal = User.objects.create_user("eltern@example.invalid", account_kind="portal")
        change, _ = submit(self.child, {"city": "Neustadt"}, portal)
        body = {"version": change.version, "decisions": {"city": "apply"}}
        response = self.client_for(self.leader).post(f"/api/v1/portal/reviews/{change.pk}/decide/", body, format="json")
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.data["code"], "own_request")
        response = self.client_for(self.colleague).post(
            f"/api/v1/portal/reviews/{change.pk}/decide/", body, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
