"""DSGVO Art. 32 hardening: MFA for member data, minimal logs, password rules. Fictional data."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from departments.models import Department, UserDepartmentRole
from jf_manager_backend.log_safety import mask_email
from users.mfa_policy import mfa_required, privileged_account

User = get_user_model()


class MfaForMemberDataTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Mitte", code="mfa-mitte")
        self.betreuer = User.objects.create_user("betreuer", password="x")
        group = Group.objects.create(name="Betreuer-Test")
        group.permissions.add(Permission.objects.get(codename="view_member"))
        UserDepartmentRole.objects.create(user=self.betreuer, department=self.department).groups.add(group)

    def test_member_readers_need_mfa_but_keep_normal_sessions(self):
        self.assertTrue(mfa_required(self.betreuer))
        self.assertFalse(privileged_account(self.betreuer))

    @override_settings(MFA_REQUIRED_FOR_MEMBER_DATA=False)
    def test_operators_can_switch_it_off(self):
        self.assertFalse(mfa_required(self.betreuer))

    def test_accounts_without_member_access_stay_optional(self):
        self.assertFalse(mfa_required(User.objects.create_user("inventar", password="x")))


class HardeningTests(TestCase):
    def test_email_addresses_are_masked_in_logs(self):
        self.assertEqual(mask_email("eva.muster@example.org"), "e***@example.org")
        self.assertEqual(mask_email(""), "***")

    def test_passwords_need_ten_characters(self):
        with self.assertRaises(ValidationError):
            validate_password("Kurz!2026")
        validate_password("Lang-genug-2026!")

    @override_settings(RQ_QUEUES={"default": {"URL": "redis://localhost:6379/0"}})
    def test_password_reset_runs_in_the_worker(self):
        with (
            patch("users.tasks.send_password_reset_job.delay") as delay,
            patch("users.api_views.send_password_reset") as direct,
        ):
            response = self.client.post("/api/v1/users/request_password_reset/", {"email": "nobody@example.invalid"})
        self.assertEqual(response.status_code, 200)
        delay.assert_called_once_with("nobody@example.invalid")
        direct.assert_not_called()
