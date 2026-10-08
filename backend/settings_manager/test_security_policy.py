from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from settings_manager.models import SecurityPolicy
from settings_manager.runtime_policy import effective_policy
from users.session_policy import ACTIVITY_KEY, PRIVILEGED_KEY, STARTED_KEY, lifetimes, session_deadlines


class SecurityPolicyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-policy")
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="settings_manager", codename__in=["view_all_settings", "change_all_settings"]
            )
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_changes_are_used_by_actual_session_expiry_for_both_profiles(self):
        response = self.client.patch(
            "/api/v1/settings/security/",
            {
                "session_idle_timeout_seconds": 1800,
                "session_max_age_seconds": 7200,
                "privileged_session_idle_timeout_seconds": 600,
                "privileged_session_max_age_seconds": 3600,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(lifetimes({}), (1800, 7200))
        self.assertEqual(lifetimes({PRIVILEGED_KEY: True}), (600, 3600))
        self.assertEqual(session_deadlines({STARTED_KEY: 100, ACTIVITY_KEY: 200})["idle_expires_at"], 2000)
        self.assertEqual(response.data["fields"]["session_idle_timeout_seconds"]["source"], "database")

    def test_invalid_partial_cross_field_update_does_not_change_saved_policy(self):
        SecurityPolicy.objects.create(session_idle_timeout_seconds=1800, session_max_age_seconds=3600)
        response = self.client.patch(
            "/api/v1/settings/security/", {"session_idle_timeout_seconds": 7200}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(lifetimes({}), (1800, 3600))

    @override_settings(
        CONFIGURATION_ENV_OVERRIDES=frozenset({"SESSION_IDLE_TIMEOUT_SECONDS"}), SESSION_IDLE_TIMEOUT_SECONDS=1200
    )
    def test_environment_override_is_effective_visible_and_write_locked(self):
        SecurityPolicy.objects.create(session_idle_timeout_seconds=600)
        response = self.client.get("/api/v1/settings/security/")
        self.assertEqual(response.data["session_idle_timeout_seconds"], 1200)
        self.assertTrue(response.data["fields"]["session_idle_timeout_seconds"]["locked"])
        self.assertEqual(response.data["fields"]["session_idle_timeout_seconds"]["source"], "environment")
        response = self.client.patch(
            "/api/v1/settings/security/", {"session_idle_timeout_seconds": 1800}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(lifetimes({})[0], 1200)

    def test_bounds_and_unknown_fields_are_rejected(self):
        for data in [
            {"session_idle_timeout_seconds": 1},
            {"privileged_session_max_age_seconds": 999999999},
            {"unknown": True},
        ]:
            response = self.client.patch("/api/v1/settings/security/", data, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(SecurityPolicy.objects.exists())

    def test_staff_without_global_configuration_rights_cannot_read_or_write(self):
        user = get_user_model().objects.create_user(username="synthetic-policy-staff", is_staff=True)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/v1/settings/security/").status_code, 403)
        self.assertEqual(self.client.patch("/api/v1/settings/security/", {}, format="json").status_code, 403)

    def test_default_source_has_no_read_side_creation(self):
        self.assertEqual(effective_policy()["fields"]["session_idle_timeout_seconds"]["source"], "default")
        self.assertFalse(SecurityPolicy.objects.exists())
