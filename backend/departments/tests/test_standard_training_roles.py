import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.models import Department, RoleTemplate, UserDepartmentRole
from training.models import TrainingBlock, TrainingSession


class StandardTrainingRoleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.a = Department.objects.create(name="Role A", code="train-role-a")
        cls.b = Department.objects.create(name="Role B", code="train-role-b")
        cls.user = get_user_model().objects.create_user(username="training-role-user")
        for department, key in ((cls.a, "training_planner"), (cls.b, "supervisor")):
            UserDepartmentRole.objects.create(user=cls.user, department=department).groups.add(
                RoleTemplate.objects.get(key=key).group
            )
        cls.sessions = {}
        cls.blocks = {}
        for department in (cls.a, cls.b):
            for state in ("draft", "published"):
                session = TrainingSession.objects.create(
                    title=f"{department.name} {state}",
                    date=datetime.date(2027, 1, 1),
                    start_time="18:00",
                    end_time="19:00",
                    department=department,
                    status=state,
                )
                cls.sessions[(department.pk, state)] = session
                cls.blocks[(department.pk, state)] = TrainingBlock.objects.create(
                    session=session, title="Block", duration_minutes=15
                )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_mixed_roles_see_own_plans_and_only_released_foreign_department_exercises(self):
        sessions = self.client.get("/api/v1/training/sessions/")
        self.assertEqual(sessions.status_code, 200)
        self.assertEqual(
            {row["id"] for row in sessions.data["results"]},
            {session.pk for (pk, state), session in self.sessions.items() if pk == self.a.pk or state != "draft"},
        )
        blocks = self.client.get("/api/v1/training/blocks/")
        self.assertEqual(blocks.status_code, 200)
        self.assertEqual(
            {row["id"] for row in blocks.data["results"]},
            {block.pk for (pk, state), block in self.blocks.items() if pk == self.a.pk or state != "draft"},
        )

    def test_draft_direct_access_handout_and_blocks_are_hidden_from_supervisor(self):
        session = self.sessions[(self.b.pk, "draft")]
        block = self.blocks[(self.b.pk, "draft")]
        for url in (
            f"/api/v1/training/sessions/{session.pk}/",
            f"/api/v1/training/sessions/{session.pk}/handout/",
            f"/api/v1/training/sessions/{session.pk}/plan/",
            f"/api/v1/training/blocks/{block.pk}/",
        ):
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_department_planner_writes_a_but_cannot_write_b_with_or_without_filter(self):
        a = self.sessions[(self.a.pk, "draft")]
        b = self.sessions[(self.b.pk, "draft")]
        self.assertEqual(
            self.client.patch(f"/api/v1/training/sessions/{a.pk}/", {"title": "Changed"}, format="json").status_code,
            200,
        )
        for suffix in ("", f"?department={self.a.pk}"):
            response = self.client.patch(f"/api/v1/training/sessions/{b.pk}/{suffix}", {"title": "Bad"}, format="json")
            self.assertIn(response.status_code, (403, 404))
        self.assertEqual(
            self.client.patch(
                f"/api/v1/training/blocks/{self.blocks[(self.b.pk, 'draft')].pk}/move/",
                {"start_offset_minutes": 10},
                format="json",
            ).status_code,
            403,
        )
        b.refresh_from_db()
        self.assertNotEqual(b.title, "Bad")

    def test_department_planner_creates_in_a_and_rejects_b_target(self):
        payload = {
            "title": "New",
            "date": "2027-01-02",
            "start_time": "18:00",
            "end_time": "19:00",
            "department": self.a.pk,
        }
        self.assertEqual(self.client.post("/api/v1/training/sessions/", payload, format="json").status_code, 201)
        payload["department"] = self.b.pk
        self.assertEqual(self.client.post("/api/v1/training/sessions/", payload, format="json").status_code, 400)

    def test_staff_without_subject_rights_cannot_read_training(self):
        user = get_user_model().objects.create_user(username="staff-no-subject", is_staff=True)
        self.client.force_authenticate(user)
        for url in ("/api/v1/training/sessions/", "/api/v1/training/blocks/"):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_destructive_model_right_is_not_implied_by_planning(self):
        session = self.sessions[(self.a.pk, "draft")]
        self.assertEqual(self.client.delete(f"/api/v1/training/sessions/{session.pk}/").status_code, 403)


class StandardOrderRoleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import Group, Permission

        from members.models import Member
        from orders.models import Order

        call_command("seed_role_templates", stdout=StringIO())
        cls.a = Department.objects.create(name="Order A", code="role-order-a")
        cls.b = Department.objects.create(name="Order B", code="role-order-b")
        cls.user = get_user_model().objects.create_user(username="order-standard-role")
        cls.member_a = Member.objects.create(name="Synthetic", lastname="A")
        cls.member_b = Member.objects.create(name="Synthetic", lastname="B")
        cls.member_a.departments.add(cls.a)
        cls.member_b.departments.add(cls.b)
        cls.order_a = Order.objects.create(member=cls.member_a, department=cls.a)
        cls.order_b = Order.objects.create(member=cls.member_b, department=cls.b)
        UserDepartmentRole.objects.create(user=cls.user, department=cls.a).groups.add(
            RoleTemplate.objects.get(key="order_manager").group
        )
        reader = Group.objects.create(name="Order B reader")
        reader.permissions.add(Permission.objects.get(content_type__app_label="orders", codename="view_order"))
        UserDepartmentRole.objects.create(user=cls.user, department=cls.b).groups.add(reader)

    def test_department_order_role_writes_a_and_rejects_read_only_b(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.patch(f"/api/v1/orders/{self.order_a.pk}/", {"notes": "Allowed"}, format="json").status_code,
            200,
        )
        self.assertEqual(
            self.client.patch(f"/api/v1/orders/{self.order_b.pk}/", {"notes": "Bad"}, format="json").status_code, 403
        )
        self.order_b.refresh_from_db()
        self.assertEqual(self.order_b.notes, "")

    def test_order_creation_target_uses_same_special_right_as_object_mutation(self):
        from orders.models import OrderableItem, OrderStatus

        item = OrderableItem.objects.create(name="Synthetic item", category="Synthetic")
        status, _ = OrderStatus.objects.get_or_create(code="NEW", defaults={"name": "Neu"})
        self.client.force_authenticate(self.user)
        payload = {
            "member": self.member_a.pk,
            "department": self.a.pk,
            "items": [{"item": item.pk, "quantity": 1, "status": status.pk}],
        }
        response = self.client.post("/api/v1/orders/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        payload.update(member=self.member_b.pk, department=self.b.pk)
        self.assertEqual(self.client.post("/api/v1/orders/", payload, format="json").status_code, 400)
