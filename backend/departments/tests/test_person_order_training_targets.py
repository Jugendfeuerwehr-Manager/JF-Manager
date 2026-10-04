"""Writes must check person, order and training relation targets."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Group, Member
from orders.models import Order, OrderableItem, OrderStatus
from qualifications.models import Qualification, QualificationType, SpecialTask, SpecialTaskType
from training.models import TrainingSession


class PersonOrderTrainingTargetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="relation-target-a")
        cls.department_b = Department.objects.create(name="B", code="relation-target-b")
        cls.member_a = Member.objects.create(name="A", lastname="Member")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b = Member.objects.create(name="B", lastname="Member")
        cls.member_b.departments.add(cls.department_b)
        cls.group_a = Group.objects.create(name="A group", department=cls.department_a)
        cls.group_b = Group.objects.create(name="B group", department=cls.department_b)
        cls.qualification_type = QualificationType.objects.create(name="Target qualification")
        cls.qualification_a = Qualification.objects.create(
            type=cls.qualification_type, member=cls.member_a, date_acquired=date(2026, 1, 1)
        )
        cls.task_type = SpecialTaskType.objects.create(name="Target task")
        cls.task_a = SpecialTask.objects.create(task=cls.task_type, member=cls.member_a, start_date=date(2026, 1, 1))
        cls.order_item = OrderableItem.objects.create(name="Jacket", category="Clothing")
        cls.order_status, _ = OrderStatus.objects.get_or_create(code="NEW", defaults={"name": "New"})
        cls.order_a = Order.objects.create(member=cls.member_a, department=cls.department_a)
        cls.session_a = TrainingSession.objects.create(
            title="A session", date=date(2026, 10, 15), start_time="10:00", end_time="11:00", department=cls.department_a
        )

        cls.user = get_user_model().objects.create_user(username="relation-target-writer")
        training_permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(TrainingSession),
            codename="can_manage_training",
            defaults={"name": "Manage training in test"},
        )
        cls.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="orders", codename="can_manage_orders"),
        )
        cls.training_user = get_user_model().objects.create_user(username="relation-target-training-writer")
        cls.training_user.user_permissions.add(training_permission)
        UserDepartmentRole.objects.create(user=cls.training_user, department=cls.department_a)
        writer = AuthGroup.objects.create(name="Relation target writer A")
        writer.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="qualifications",
                codename__in=["add_qualification", "change_qualification", "add_specialtask", "change_specialtask"],
            ),
            Permission.objects.get(content_type__app_label="orders", codename="add_order"),
            Permission.objects.get(content_type__app_label="orders", codename="change_order"),
        )
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_a).groups.add(writer)
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_b)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def _order_data(self, member, department):
        return {
            "member": member.pk,
            "department": department.pk,
            "items": [{"item": self.order_item.pk, "size": "M", "quantity": 1, "status": self.order_status.pk}],
        }

    def _session_data(self, department, groups):
        return {
            "title": "Target session",
            "date": "2026-10-15",
            "start_time": "10:00",
            "end_time": "11:00",
            "department": department.pk,
            "group_ids": [group.pk for group in groups],
        }

    def test_qualification_cannot_be_created_for_read_only_member(self):
        response = self.client.post(
            "/api/v1/qualifications/",
            {"type": self.qualification_type.pk, "member": self.member_b.pk, "date_acquired": "2026-10-01"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Qualification.objects.filter(member=self.member_b).exists())

    def test_qualification_cannot_be_moved_to_read_only_member(self):
        response = self.client.patch(
            f"/api/v1/qualifications/{self.qualification_a.pk}/", {"member": self.member_b.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.qualification_a.refresh_from_db()
        self.assertEqual(self.qualification_a.member_id, self.member_a.pk)

    def test_special_task_cannot_be_created_for_read_only_member(self):
        response = self.client.post(
            "/api/v1/qualifications/specialtasks/",
            {"task": self.task_type.pk, "member": self.member_b.pk, "start_date": "2026-10-01"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SpecialTask.objects.filter(member=self.member_b).exists())

    def test_special_task_cannot_be_moved_to_read_only_member(self):
        response = self.client.patch(
            f"/api/v1/qualifications/specialtasks/{self.task_a.pk}/", {"member": self.member_b.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.task_a.refresh_from_db()
        self.assertEqual(self.task_a.member_id, self.member_a.pk)

    def test_order_cannot_be_created_in_read_only_department(self):
        response = self.client.post(
            "/api/v1/orders/", self._order_data(self.member_b, self.department_b), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.filter(member=self.member_b).exists())

    def test_order_cannot_link_member_from_other_department(self):
        response = self.client.post(
            "/api/v1/orders/", self._order_data(self.member_b, self.department_a), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.filter(member=self.member_b).exists())

    def test_order_cannot_be_moved_to_read_only_department(self):
        response = self.client.patch(
            f"/api/v1/orders/{self.order_a.pk}/", {"department": self.department_b.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.department_id, self.department_a.pk)

    def test_order_cannot_be_moved_to_read_only_member(self):
        response = self.client.patch(
            f"/api/v1/orders/{self.order_a.pk}/", {"member": self.member_b.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.member_id, self.member_a.pk)

    def test_training_cannot_be_created_in_read_only_department(self):
        self.client.force_authenticate(user=self.training_user)
        response = self.client.post(
            "/api/v1/training/sessions/", self._session_data(self.department_b, [self.group_b]), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(TrainingSession.objects.filter(department=self.department_b).exists())

    def test_training_cannot_link_group_from_other_department(self):
        self.client.force_authenticate(user=self.training_user)
        response = self.client.post(
            "/api/v1/training/sessions/", self._session_data(self.department_a, [self.group_b]), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(TrainingSession.objects.filter(title="Target session").exists())

    def test_training_cannot_move_to_read_only_department(self):
        self.client.force_authenticate(user=self.training_user)
        response = self.client.patch(
            f"/api/v1/training/sessions/{self.session_a.pk}/",
            {"department": self.department_b.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.session_a.refresh_from_db()
        self.assertEqual(self.session_a.department_id, self.department_a.pk)

    def test_training_cannot_link_group_from_other_department_on_update(self):
        self.client.force_authenticate(user=self.training_user)
        response = self.client.patch(
            f"/api/v1/training/sessions/{self.session_a.pk}/",
            {"group_ids": [self.group_b.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.session_a.groups.exists())

    def test_qualification_can_be_created_for_writable_member(self):
        response = self.client.post(
            "/api/v1/qualifications/",
            {"type": self.qualification_type.pk, "member": self.member_a.pk, "date_acquired": "2026-10-01"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_order_can_be_created_for_writable_member(self):
        response = self.client.post(
            "/api/v1/orders/", self._order_data(self.member_a, self.department_a), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_training_can_be_created_with_group_from_own_department(self):
        self.client.force_authenticate(user=self.training_user)
        response = self.client.post(
            "/api/v1/training/sessions/", self._session_data(self.department_a, [self.group_a]), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
