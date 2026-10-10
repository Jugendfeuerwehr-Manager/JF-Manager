"""PORTAL-02.1/02.2: release policy, member portal switch and the person view."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from inventory.models import Item, ItemVariant, StorageLocation
from inventory.opening_stock import book_opening_stock
from members.models import Group as MemberGroup
from members.models import Member, Parent
from portal.disclosure import ALLOWED_KEYS
from portal.models import AccountLink, PortalPolicy
from portal.policy import PolicySet, member_portal_allowed
from qualifications.models import Qualification, QualificationType

User = get_user_model()
MARKER = "GEHEIM-MARKER-2b"


def born(years, days=0):
    today = timezone.localdate()
    return date(today.year - years, today.month, min(today.day, 28)) - timedelta(days=days)


class PolicyLogicTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.nord = Department.objects.create(name="Nord")

    def test_defaults_without_rows(self):
        policies = PolicySet.load()
        self.assertTrue(policies.visible("qualifications", "parents", [self.mitte.pk]))
        self.assertFalse(policies.visible("equipment", "parents", [self.mitte.pk]))
        self.assertTrue(policies.visible("contact", "members", []))
        self.assertFalse(policies.visible("other_parents", "members", [self.mitte.pk]))  # not a member category

    def test_department_releases_within_the_ceiling_and_multi_department(self):
        PortalPolicy.objects.create(department=None, ceiling={"identity": {"parents": "locked"}})
        PortalPolicy.objects.create(
            department=self.nord,
            visibility={"equipment": {"parents": "visible"}, "identity": {"parents": "visible"}},
        )
        policies = PolicySet.load()
        self.assertFalse(policies.visible("equipment", "parents", [self.mitte.pk]))
        self.assertTrue(policies.visible("equipment", "parents", [self.mitte.pk, self.nord.pk]))  # D2
        self.assertFalse(policies.visible("identity", "parents", [self.nord.pk]))  # locked wins

    def test_member_portal_modes(self):
        member = Member.objects.create(name="Jo", birthday=born(15))
        member.departments.add(self.mitte, self.nord)
        self.assertFalse(member_portal_allowed(member))  # organisation default off (D3)
        PortalPolicy.objects.create(department=self.mitte, member_portal_mode="min_age", member_portal_min_age=16)
        self.assertFalse(member_portal_allowed(member))
        PortalPolicy.objects.create(department=self.nord, member_portal_mode="min_age", member_portal_min_age=14)
        self.assertTrue(member_portal_allowed(member))  # one department suffices (D2)
        unknown = Member.objects.create(name="Ohne")
        unknown.departments.add(self.nord)
        self.assertFalse(member_portal_allowed(unknown))  # min_age without birthday is not met
        PortalPolicy.objects.create(department=None, member_portal_mode="all")
        other = Member.objects.create(name="Ole")
        self.assertTrue(member_portal_allowed(other) is False)  # no department at all


class PersonViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        group = MemberGroup.objects.create(name="Gruppe 2", department=cls.mitte)
        cls.child = Member.objects.create(
            name="Mia",
            lastname="Beispiel",
            birthday=born(12),
            group=group,
            notes=MARKER,
            identityCardNumber="JF-1",
            street="Lindenweg 4",
        )
        cls.child.departments.add(cls.mitte)
        cls.parent = Parent.objects.create(name="Eva", lastname="Beispiel", phone="0151", notes=MARKER)
        cls.other_parent = Parent.objects.create(name="Paul", lastname="Beispiel", phone="0170", notes=MARKER)
        for parent in (cls.parent, cls.other_parent):
            parent.children.add(cls.child)
        qtype = QualificationType.objects.create(name="Jugendflamme 1")
        Qualification.objects.create(type=qtype, member=cls.child, date_acquired=born(1), note=MARKER, issued_by=MARKER)
        location = StorageLocation.objects.create(name="Mia", is_member=True, member=cls.child)
        book_opening_stock(location, 1, item=Item.objects.create(name="Helm"))
        cls.stranger = Member.objects.create(name="Fremd", birthday=born(10))
        cls.stranger.departments.add(cls.mitte)
        cls.user = User.objects.create_user("eva@example.invalid", password="x", account_kind="portal")
        AccountLink.objects.create(user=cls.user, parent=cls.parent, status="confirmed")

    def setUp(self):
        self.client.force_login(self.user)

    def get(self, member):
        return self.client.get(f"/api/v1/portal/people/{member.pk}/")

    def test_default_release(self):
        data = self.get(self.child).json()
        self.assertEqual(data["contact"]["street"], "Lindenweg 4")
        self.assertEqual(data["age"], 12)
        self.assertEqual(data["group"], {"group": "Gruppe 2", "departments": ["Mitte"]})
        self.assertEqual(data["qualifications"][0]["type"], "Jugendflamme 1")
        for hidden in ("membership", "identity", "swimming", "special_tasks", "equipment", "other_parents"):
            self.assertNotIn(hidden, data)
        self.assertNotIn(MARKER, str(data))

    def test_everything_released_still_leaks_nothing_internal(self):
        released = {
            key: {"parents": "visible"}
            for key in ("membership", "identity", "swimming", "special_tasks", "equipment", "other_parents")
        }
        PortalPolicy.objects.create(department=None, visibility=released)
        data = self.get(self.child).json()
        self.assertLessEqual(set(data), ALLOWED_KEYS)
        self.assertEqual(data["identity"], {"card_number": "JF-1"})
        self.assertEqual(data["equipment"], [{"item": "Helm", "variant": "", "quantity": 1}])
        self.assertEqual([p["name"] for p in data["other_parents"]], ["Paul Beispiel"])
        self.assertEqual(set(data["qualifications"][0]), {"type", "acquired", "expires", "valid"})
        self.assertNotIn(MARKER, str(data))

    def test_variant_equipment_can_be_viewed_and_contact_change_requested(self):
        PortalPolicy.objects.create(department=None, visibility={"equipment": {"parents": "visible"}})
        variant = ItemVariant.objects.create(
            parent_item=Item.objects.create(name="Hose"), variant_attributes={"Größe": "164"}
        )
        book_opening_stock(self.child.personal_storage_location, 2, item_variant=variant)
        response = self.get(self.child)
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json()["equipment"],
            [
                {"item": "Helm", "variant": "", "quantity": 1},
                {"item": "Hose", "variant": "Hose (Größe: 164)", "quantity": 2},
            ],
        )
        self.assertNotIn(MARKER, str(response.json()))
        response = self.client.post(
            "/api/v1/portal/change-requests/",
            {"target": {"kind": "member", "id": self.child.pk}, "fields": {"street": "Beispielweg 5"}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "open")
        self.child.refresh_from_db()
        self.assertEqual(self.child.street, "Lindenweg 4")
        self.assertEqual(self.get(self.stranger).status_code, 404)

    def test_foreign_and_adult_children_are_404(self):
        self.assertEqual(self.get(self.stranger).status_code, 404)
        Member.objects.filter(pk=self.child.pk).update(birthday=born(18, days=1))
        self.assertEqual(self.get(self.child).status_code, 404)

    def test_me_contains_own_parent_record(self):
        data = self.client.get("/api/v1/portal/me/").json()
        self.assertEqual(data["parent"]["phone"], "0151")
        self.assertNotIn("notes", data["parent"])


class PolicyApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.nord = Department.objects.create(name="Nord")
        cls.editors = Group.objects.create(name="Freigaben")
        cls.editors.permissions.add(Permission.objects.get(codename="change_portalpolicy"))
        cls.staff = User.objects.create_user("leitung.mitte", password="x")
        UserDepartmentRole.objects.create(user=cls.staff, department=cls.mitte).groups.add(cls.editors)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def test_overview_scoped_to_departments(self):
        data = self.client.get("/api/v1/portal/policies/").json()
        self.assertFalse(data["organization"]["editable"])
        self.assertEqual([d["name"] for d in data["departments"]], ["Mitte"])
        self.assertIn("Bemerkungen", data["never_visible"])
        self.assertEqual(
            data["departments"][0]["effective"]["qualifications"], {"parents": "visible", "members": "visible"}
        )

    def test_department_update_versioned_and_within_ceiling(self):
        payload = {
            "version": 0,
            "visibility": {"equipment": {"parents": "visible"}},
            "member_portal_mode": "min_age",
            "member_portal_min_age": 14,
        }
        response = self.client.put(f"/api/v1/portal/policies/{self.mitte.pk}/", payload, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        row = response.json()["departments"][0]
        self.assertEqual(row["effective"]["equipment"]["parents"], "visible")
        self.assertEqual(row["version"], 1)
        self.assertEqual(
            self.client.put(f"/api/v1/portal/policies/{self.mitte.pk}/", payload, format="json").status_code, 409
        )
        PortalPolicy.objects.create(department=None, ceiling={"swimming": {"parents": "locked"}})
        locked = self.client.put(
            f"/api/v1/portal/policies/{self.mitte.pk}/",
            {"version": 1, "visibility": {"swimming": {"parents": "visible"}}},
            format="json",
        )
        self.assertEqual(locked.status_code, 400)
        fixed = self.client.put(
            f"/api/v1/portal/policies/{self.mitte.pk}/",
            {"version": 1, "visibility": {"contact": {"parents": "hidden"}}},
            format="json",
        )
        self.assertEqual(fixed.status_code, 400)

    def test_rights(self):
        self.assertEqual(
            self.client.put(f"/api/v1/portal/policies/{self.nord.pk}/", {"version": 0}, format="json").status_code, 403
        )
        self.assertEqual(
            self.client.put("/api/v1/portal/policies/org/", {"version": 0}, format="json").status_code, 403
        )
        self.client.force_authenticate(User.objects.create_user("ohne", password="x"))
        self.assertEqual(self.client.get("/api/v1/portal/policies/").status_code, 403)
        portal = User.objects.create_user("p@example.invalid", password="x", account_kind="portal")
        browser = self.client_class()
        browser.force_login(portal)
        self.assertEqual(browser.get("/api/v1/portal/policies/").status_code, 403)

    def test_organisation_update_needs_org_scope(self):
        admin = User.objects.create_superuser("admin", password="x")
        self.client.force_authenticate(admin)
        response = self.client.put(
            "/api/v1/portal/policies/org/",
            {"version": 0, "member_portal_mode": "all", "ceiling": {"identity": {"parents": "locked"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["organization"]["ceiling"]["identity"]["parents"], "locked")
        self.assertEqual(response.json()["organization"]["member_portal_mode"], "all")
