"""PORTAL-04.1: link staff accounts to member and parent records (E13, Q4)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent
from notifications.models import EmailDelivery, InboxItem
from portal.models import AccountLink, Invitation
from portal.people import confirmed_link, portal_children, portal_self

User = get_user_model()
URL = "/api/v1/portal/account-links/"


def account_admin(username, department):
    group, _ = Group.objects.get_or_create(name="Kontoverwaltung")
    group.permissions.add(Permission.objects.get(codename="change_customuser", content_type__app_label="users"))
    user = User.objects.create_user(username, password="x", first_name="Kai", last_name="Verwalter")
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)
    return user


class AccountLinkApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.nord = Department.objects.create(name="Nord")
        cls.admin = User.objects.create_superuser("admin", password="x", first_name="Alex", last_name="Sommer")
        cls.manager = account_admin("kontoverwaltung", cls.mitte)
        cls.leader = User.objects.create_user(
            "leitung", password="x", first_name="Tobias", last_name="Lehmann", email="tobias@example.invalid"
        )
        cls.other_staff = User.objects.create_user("betreuer", password="x", first_name="Jan", last_name="Keller")
        cls.member = Member.objects.create(name="Tobias", lastname="Lehmann", email="tobias@example.invalid")
        cls.member.departments.add(cls.mitte)
        cls.member_nord = Member.objects.create(name="Nora", lastname="Nord")
        cls.member_nord.departments.add(cls.nord)
        cls.child = Member.objects.create(name="Ella", lastname="Lehmann")
        cls.child.departments.add(cls.mitte)
        cls.parent = Parent.objects.create(name="Tobias", lastname="Lehmann")
        cls.parent.children.add(cls.child)

    def client_for(self, user):
        # Portal accounts need a real session (the boundary middleware); staff skips the MFA policy here.
        client = APIClient()
        if user.is_portal_account:
            client.force_login(user)
        else:
            client.force_authenticate(user)
        return client

    def link(self, actor, **data):
        return self.client_for(actor).post(URL, {"user": self.leader.pk, **data}, format="json")

    def test_new_link_is_pending_without_effect_and_notifies_the_account(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.link(self.admin, member=self.member.pk, parent=self.parent.pk)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["member"]["birth_year"], None)
        self.assertEqual(response.data["parent"]["children"][0]["first_name"], "Ella")
        self.assertIsNone(confirmed_link(self.leader))
        self.assertIsNone(portal_self(self.leader))
        self.assertFalse(portal_children(self.leader).exists())
        notice = InboxItem.objects.get(kind="account_link")
        self.assertTrue(notice.recipients.filter(user=self.leader).exists())
        self.assertEqual(notice.link, "/konto-bestaetigen")
        self.assertEqual(EmailDelivery.objects.filter(kind="account_link", user=self.leader).count(), 1)

    def test_member_cannot_be_bound_twice(self):
        self.link(self.admin, member=self.member.pk)
        response = self.client_for(self.admin).post(
            URL, {"user": self.other_staff.pk, "member": self.member.pk}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "record_linked")

    def test_account_cannot_get_a_second_member(self):
        self.link(self.admin, member=self.member.pk)
        response = self.link(self.admin, member=self.member_nord.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "account_linked")

    def test_repeating_the_same_link_changes_nothing(self):
        self.link(self.admin, member=self.member.pk)
        response = self.link(self.admin, member=self.member.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccountLink.objects.count(), 1)

    def test_record_with_portal_account_conflicts(self):
        portal = User.objects.create_user("eltern@example.invalid", password="x", account_kind="portal")
        AccountLink.objects.create(user=portal, member=self.member, status="confirmed")
        response = self.link(self.manager, member=self.member.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "record_has_portal_account")
        # Even a transfer request needs system administration.
        response = self.link(self.manager, member=self.member.pk, transfer=True)
        self.assertEqual(response.status_code, 409)

    def test_system_administration_converts_a_portal_account(self):
        portal = User.objects.create_user("mitglied@example.invalid", password="x", account_kind="portal")
        AccountLink.objects.create(user=portal, member=self.member, status="confirmed")
        response = self.link(self.admin, member=self.member.pk, transfer=True)
        self.assertEqual(response.status_code, 201, response.content)
        portal.refresh_from_db()
        self.assertFalse(portal.is_active)
        self.assertFalse(AccountLink.objects.filter(user=portal).exists())
        self.assertEqual(AccountLink.objects.get(member=self.member).user, self.leader)

    def test_portal_accounts_are_never_linked_here(self):
        portal = User.objects.create_user("p@example.invalid", password="x", account_kind="portal")
        response = self.client_for(self.admin).post(URL, {"user": portal.pk, "member": self.member.pk}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "portal_account")

    def test_open_invitation_blocks_linking(self):
        Invitation.objects.create(
            member=self.member, email="x@example.invalid", token_hash="a" * 64, expires_at="2099-01-01T00:00Z"
        )
        response = self.link(self.admin, member=self.member.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "invitation_open")

    def test_rights_missing_right_and_foreign_department(self):
        self.assertEqual(self.link(self.other_staff, member=self.member.pk).status_code, 403)
        self.assertEqual(self.client_for(self.other_staff).get(URL).status_code, 403)
        self.assertEqual(self.link(self.manager, member=self.member_nord.pk).status_code, 404)
        self.assertEqual(self.link(self.manager, member=self.member.pk).status_code, 201)
        # Parent records count through their children's departments.
        self.assertEqual(self.link(self.manager, parent=self.parent.pk).status_code, 201)

    def test_own_account_is_linked_by_someone_else(self):
        response = self.client_for(self.manager).post(
            URL, {"user": self.manager.pk, "member": self.member.pk}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "own_account")

    def test_portal_account_gets_403(self):
        portal = User.objects.create_user("q@example.invalid", password="x", account_kind="portal")
        client = self.client_for(portal)
        for method, path in (("get", URL), ("get", f"{URL}pending-for-me/"), ("post", URL)):
            response = getattr(client, method)(path, {}, format="json")
            self.assertEqual(response.status_code, 403, path)
            self.assertEqual(response.json()["code"], "portal_account_forbidden")

    def test_list_and_suggestions_stay_in_scope(self):
        self.link(self.admin, member=self.member.pk)
        rows = self.client_for(self.manager).get(URL, {"member": self.member.pk}).data["results"]
        self.assertEqual([row["user"]["id"] for row in rows], [self.leader.pk])
        suggestions = self.client_for(self.manager).get(f"{URL}suggestions/", {"user": self.leader.pk}).data["results"]
        self.assertIn(("member", self.member.pk, "email"), [(s["kind"], s["id"], s["reason"]) for s in suggestions])
        self.assertNotIn(self.member_nord.pk, [s["id"] for s in suggestions])
        accounts = self.client_for(self.manager).get(f"{URL}suggestions/", {"member": self.member.pk}).data["results"]
        self.assertEqual(accounts[0]["id"], self.leader.pk)
        self.assertEqual(
            self.client_for(self.manager).get(f"{URL}suggestions/", {"member": self.member_nord.pk}).status_code, 404
        )

    def test_account_search_lists_staff_accounts_only(self):
        User.objects.create_user("portal@example.invalid", password="x", account_kind="portal", first_name="Tobias")
        rows = self.client_for(self.manager).get(f"{URL}accounts/", {"search": "tobias"}).data["results"]
        self.assertEqual([row["id"] for row in rows], [self.leader.pk])
        self.assertEqual(self.client_for(self.other_staff).get(f"{URL}accounts/").status_code, 403)

    def test_unlink_whole_link_or_one_record(self):
        link_id = self.link(self.admin, member=self.member.pk, parent=self.parent.pk).data["id"]
        response = self.client_for(self.manager).delete(f"{URL}{link_id}/?target=parent")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["parent"])
        response = self.client_for(self.manager).delete(f"{URL}{link_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(AccountLink.objects.exists())

    def test_unlink_needs_scope(self):
        link_id = self.link(self.admin, member=self.member_nord.pk).data["id"]
        self.assertEqual(self.client_for(self.manager).delete(f"{URL}{link_id}/").status_code, 404)
        self.assertEqual(self.client_for(self.other_staff).delete(f"{URL}{link_id}/").status_code, 403)


class AccountLinkDecisionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.admin = User.objects.create_superuser("admin", password="x", first_name="Alex", last_name="Sommer")
        cls.leader = User.objects.create_user("leitung", password="x", first_name="Tobias", last_name="Lehmann")
        cls.other = User.objects.create_user("betreuer", password="x")
        cls.member = Member.objects.create(name="Tobias", lastname="Lehmann")
        cls.member.departments.add(cls.mitte)
        cls.parent = Parent.objects.create(name="Tobias", lastname="Lehmann")
        cls.child = Member.objects.create(name="Ella", lastname="Lehmann")
        cls.child.departments.add(cls.mitte)
        cls.parent.children.add(cls.child)

    def setUp(self):
        self.link = AccountLink.objects.create(user=self.leader, member=self.member, linked_by=self.admin)

    def client_for(self, user):
        # Portal accounts need a real session (the boundary middleware); staff skips the MFA policy here.
        client = APIClient()
        if user.is_portal_account:
            client.force_login(user)
        else:
            client.force_authenticate(user)
        return client

    def test_pending_for_me_shows_only_the_own_link(self):
        data = self.client_for(self.leader).get(f"{URL}pending-for-me/").data
        self.assertEqual(data["link"]["member"]["name"], "Tobias Lehmann")
        self.assertIsNone(self.client_for(self.other).get(f"{URL}pending-for-me/").data["link"])

    def test_confirm_takes_effect_and_notifies_the_linking_person(self):
        self.assertEqual(self.client_for(self.other).post(f"{URL}{self.link.pk}/confirm/").status_code, 404)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.leader).post(f"{URL}{self.link.pk}/confirm/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "confirmed")
        self.assertEqual(portal_self(self.leader), self.member)
        notice = InboxItem.objects.get(kind="account_link")
        self.assertTrue(notice.recipients.filter(user=self.admin).exists())
        self.assertIn("bestätigt", notice.title)
        # Deciding again is a no-op; the other decision is refused.
        self.assertEqual(self.client_for(self.leader).post(f"{URL}{self.link.pk}/confirm/").status_code, 200)
        self.assertEqual(self.client_for(self.leader).post(f"{URL}{self.link.pk}/reject/").status_code, 409)

    def test_reject_reports_back_and_frees_the_record(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.leader).post(f"{URL}{self.link.pk}/reject/")
        self.assertEqual(response.data["status"], "rejected")
        self.assertIsNone(portal_self(self.leader))
        self.assertIn("abgelehnt", InboxItem.objects.get(kind="account_link").title)
        response = self.client_for(self.admin).post(
            URL, {"user": self.other.pk, "member": self.member.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(AccountLink.objects.filter(user=self.leader).exists())

    def test_adding_the_parent_record_asks_for_confirmation_again(self):
        self.link.status = "confirmed"
        self.link.save()
        response = self.client_for(self.admin).post(
            URL, {"user": self.leader.pk, "parent": self.parent.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["member"]["id"], self.member.pk)
        self.assertIsNone(confirmed_link(self.leader))

    def test_release_request_creates_one_task_until_released(self):
        self.link.status = "confirmed"
        self.link.save()
        client = self.client_for(self.leader)
        self.assertTrue(client.post(f"{URL}release-request/").data["new"])
        self.assertFalse(client.post(f"{URL}release-request/").data["new"])
        task = InboxItem.objects.get(kind="account_link_release")
        self.assertTrue(task.recipients.filter(user=self.admin).exists())
        self.client_for(self.admin).delete(f"{URL}{self.link.pk}/")
        task.refresh_from_db()
        self.assertEqual(task.task_state, "done")

    def test_release_request_needs_a_confirmed_link(self):
        self.assertEqual(self.client_for(self.leader).post(f"{URL}release-request/").status_code, 404)
