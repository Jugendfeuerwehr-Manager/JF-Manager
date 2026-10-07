from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from dynamic_preferences.models import GlobalPreferenceModel
from rest_framework.test import APIClient


class ConfigurationCatalogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-catalog")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def grant(self, *names):
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="settings_manager", codename__in=names)
        )
        self.client.force_authenticate(get_user_model().objects.get(pk=self.user.pk))

    def test_defaults_are_safe_for_normal_accounts_but_admin_catalog_is_forbidden(self):
        response = self.client.get("/api/v1/settings/client-defaults/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["training_start_time"], "18:00")
        self.assertFalse(any("password" in name or "secret" in name for name in response.data))
        self.assertEqual(self.client.get("/api/v1/settings/catalog/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/settings/setup/").status_code, 403)

    def test_catalog_is_filtered_and_includes_field_contracts_without_values(self):
        self.grant("view_email_settings")
        response = self.client.get("/api/v1/settings/catalog/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(set(response.data["categories"]), {"email"})
        field = response.data["categories"]["email"]["fields"]["email_host_password"]
        self.assertTrue(field["secret"])
        self.assertEqual(field["storage"], "encrypted_preference")
        self.assertNotIn("value", field)
        self.assertFalse(response.data["host"])

    def test_entire_catalog_has_readable_labels_and_storage_contracts(self):
        self.grant("view_all_settings")
        response = self.client.get("/api/v1/settings/catalog/")
        self.assertEqual(response.status_code, 200, response.data)
        for category in response.data["categories"].values():
            for field in category["fields"].values():
                self.assertTrue(field["label"])
                self.assertIn(field["source"], {"database", "default", "environment", "computed"})
                self.assertTrue(field["effective"])
        self.assertTrue(response.data["host"])
        self.assertEqual(self.client.get("/api/v1/settings/setup/").status_code, 200)

    def test_training_defaults_validate_merged_times_atomically_and_reach_actual_clients(self):
        self.grant("view_general_settings", "change_general_settings")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                "/api/v1/settings/training/",
                {"training_start_time": "19:00", "default_block_duration_minutes": 30},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        invalid = self.client.patch(
            "/api/v1/settings/training/",
            {"training_end_time": "18:30", "default_block_duration_minutes": 50},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        defaults = self.client.get("/api/v1/settings/client-defaults/").data
        self.assertEqual(defaults["training_start_time"], "19:00")
        self.assertEqual(defaults["default_block_duration_minutes"], 30)

    def test_vocabulary_is_validated_and_published_to_authenticated_navigation_only(self):
        self.grant("change_general_settings")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch("/api/v1/settings/vocabulary/", {"training_label": "Training"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get("/api/v1/settings/client-defaults/").data["training_label"], "Training")
        self.assertEqual(
            self.client.patch("/api/v1/settings/vocabulary/", {"member_label": ""}, format="json").status_code, 400
        )
        self.assertNotIn("member_label", self.client.get("/api/v1/app/branding/").data)

    def test_staff_alone_cannot_modify_defaults_or_query_setup(self):
        self.user.is_staff = True
        self.user.save()
        self.assertEqual(
            self.client.patch(
                "/api/v1/settings/training/", {"default_block_duration_minutes": 30}, format="json"
            ).status_code,
            403,
        )
        self.assertFalse(GlobalPreferenceModel.objects.filter(section="training").exists())
