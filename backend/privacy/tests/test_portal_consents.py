"""Parents grant and withdraw consents per child in the portal; admins define kinds. Fictional data."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent
from notifications.models import EmailDelivery, InboxItem, InboxRecipient
from portal.models import AccountLink
from privacy.models import ConsentKind, ConsentRecord

User = get_user_model()
URL = "/api/v1/portal/consents/"
KINDS = "/api/v1/privacy/consent-kinds/"


@override_settings(RQ_QUEUES={})
class PortalConsentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte", code="pc-mitte")
        cls.nord = Department.objects.create(name="Nord", code="pc-nord")
        jugendwart = Group.objects.create(name="Jugendwart")
        jugendwart.permissions.add(Permission.objects.get(codename="anonymize_member"))
        cls.director = User.objects.create_user("jugendwart", password="x", email="jw@example.invalid")
        UserDepartmentRole.objects.create(user=cls.director, department=cls.mitte).groups.add(jugendwart)
        cls.other_director = User.objects.create_user("nord", password="x", email="nord@example.invalid")
        UserDepartmentRole.objects.create(user=cls.other_director, department=cls.nord).groups.add(jugendwart)
        cls.child = Member.objects.create(name="Mia", lastname="Becker")
        cls.child.departments.add(cls.mitte)
        cls.stranger = Member.objects.create(name="Ole", lastname="Fremd")
        cls.stranger.departments.add(cls.mitte)
        cls.parent = Parent.objects.create(name="Sandra", lastname="Becker")
        cls.parent.children.add(cls.child)
        cls.portal_user = User.objects.create_user("sandra", password="x", account_kind="portal")
        AccountLink.objects.create(user=cls.portal_user, parent=cls.parent, status="confirmed")
        cls.photo = ConsentKind.objects.get(slug="photo_public")
        ConsentKind.objects.filter(slug="photo_public").update(description="Fotos dürfen veröffentlicht werden.")

    def portal(self):
        client = APIClient()
        client.force_authenticate(self.portal_user)
        return client

    def change(self, status, member=None, kind="photo_public"):
        return self.portal().post(
            URL, {"member": (member or self.child).pk, "kind": kind, "status": status}, format="json"
        )

    def test_anonymous_is_rejected(self):
        self.assertIn(APIClient().get(URL).status_code, (401, 403))

    def test_staff_accounts_have_no_portal_consents(self):
        client = APIClient()
        client.force_authenticate(self.director)
        self.assertEqual(client.get(URL).status_code, 403)

    def test_foreign_child_and_kinds_outside_the_portal_look_missing(self):
        self.assertEqual(self.change("granted", member=self.stranger).status_code, 404)
        self.assertEqual(self.change("granted", kind="privacy_notice_ack").status_code, 404)
        self.assertFalse(ConsentRecord.objects.exists())

    def test_overview_lists_portal_kinds_per_child(self):
        data = self.portal().get(URL).json()
        self.assertEqual({k["slug"] for k in data["kinds"]}, {"photo_internal", "photo_public"})
        self.assertEqual([p["member_id"] for p in data["people"]], [self.child.pk])
        self.assertIsNone(data["people"][0]["consents"]["photo_public"])

    def test_grant_and_withdraw_are_logged_and_reach_the_youth_director(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.change("granted").status_code, 201)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.change("withdrawn")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["people"][0]["consents"]["photo_public"]["status"], "withdrawn")

        rows = list(ConsentRecord.objects.filter(member=self.child).order_by("recorded_at", "pk"))
        self.assertEqual([r.status for r in rows], ["granted", "withdrawn"])
        self.assertEqual({(r.source, r.recorded_by_id) for r in rows}, {("self", self.portal_user.pk)})
        self.assertEqual(rows[0].text_snapshot, "Fotos dürfen veröffentlicht werden.")

        items = InboxItem.objects.filter(kind="consent_changed")
        self.assertEqual(items.count(), 2)
        self.assertEqual(
            set(InboxRecipient.objects.filter(item__in=items).values_list("user_id", flat=True)), {self.director.pk}
        )
        self.assertNotIn("Fotos dürfen", " ".join(items.values_list("title", flat=True)))
        self.assertEqual(
            set(EmailDelivery.objects.filter(kind="consent_changed").values_list("user_id", flat=True)),
            {self.director.pk},
        )

    def test_repeating_the_current_state_logs_nothing(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.change("granted")
            self.assertEqual(self.change("granted").status_code, 200)
        self.assertEqual(ConsentRecord.objects.count(), 1)


class ConsentKindApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user("leiter", password="x")
        cls.admin = User.objects.create_user("datenschutz", password="x")
        cls.admin.user_permissions.add(
            *Permission.objects.filter(codename__in=["view_privacy_settings", "change_privacy_settings"])
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_anonymous_is_rejected(self):
        self.assertIn(APIClient().get(KINDS).status_code, (401, 403))

    def test_staff_read_but_cannot_change_kinds(self):
        client = self.client_for(self.staff)
        self.assertEqual(client.get(KINDS).status_code, 200)
        self.assertEqual(client.post(KINDS, {"slug": "x", "label": "X"}, format="json").status_code, 403)

    def test_admin_adds_a_kind_and_a_new_wording_raises_the_version(self):
        client = self.client_for(self.admin)
        created = client.post(
            KINDS,
            {"slug": "ausfahrt", "label": "Teilnahme an Ausfahrten", "description": "A", "in_portal": True},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        url = f"{KINDS}{created.json()['id']}/"
        self.assertEqual(client.patch(url, {"label": "Ausfahrten"}, format="json").json()["version"], 1)
        self.assertEqual(client.patch(url, {"description": "B"}, format="json").json()["version"], 2)
        self.assertEqual(client.delete(url).status_code, 204)

    def test_built_in_kinds_are_only_deactivated(self):
        kind = ConsentKind.objects.get(slug="photo_internal")
        client = self.client_for(self.admin)
        self.assertEqual(client.delete(f"{KINDS}{kind.pk}/").status_code, 409)
        self.assertEqual(client.patch(f"{KINDS}{kind.pk}/", {"slug": "neu"}, format="json").status_code, 400)
        self.assertFalse(client.patch(f"{KINDS}{kind.pk}/", {"active": False}, format="json").json()["active"])


class StaffConsentTests(TestCase):
    def test_inactive_kinds_can_be_withdrawn_but_not_granted(self):
        mitte = Department.objects.create(name="Mitte", code="sc-mitte")
        group = Group.objects.create(name="Leitung")
        group.permissions.add(*Permission.objects.filter(codename__in=["view_member", "change_member"]))
        leader = User.objects.create_user("leiter", password="x")
        UserDepartmentRole.objects.create(user=leader, department=mitte).groups.add(group)
        child = Member.objects.create(name="Mia", lastname="Becker")
        child.departments.add(mitte)
        client = APIClient()
        client.force_authenticate(leader)
        url = "/api/v1/privacy/consents/"
        granted = client.post(url, {"member": child.pk, "kind": "dsgvo_internal", "status": "granted"}, format="json")
        self.assertEqual(granted.status_code, 400)
        withdrawn = client.post(
            url, {"member": child.pk, "kind": "dsgvo_internal", "status": "withdrawn"}, format="json"
        )
        self.assertEqual(withdrawn.status_code, 201, withdrawn.content)
        self.assertEqual(
            withdrawn.json()["kind_label"], "Einwilligung zur internen Datenweitergabe (früheres Kennzeichen)"
        )
