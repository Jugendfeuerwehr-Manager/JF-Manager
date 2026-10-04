from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from training.models import LibraryBlock, TrainingSession


class TrainingManagementPermissionTests(TestCase):
    def test_training_and_library_permissions_are_installed_for_their_models(self):
        for model, codename in (
            (TrainingSession, "can_manage_training"),
            (LibraryBlock, "can_manage_library"),
        ):
            with self.subTest(codename=codename):
                self.assertIn(codename, {code for code, _ in model._meta.permissions})
                self.assertTrue(
                    Permission.objects.filter(
                        content_type=ContentType.objects.get_for_model(model),
                        codename=codename,
                    ).exists()
                )

    def test_permissions_are_granted_independently_and_not_by_staff_status(self):
        user = get_user_model().objects.create_user(username="training-permission-check", is_staff=True)
        self.assertFalse(user.has_perm("training.can_manage_training"))
        self.assertFalse(user.has_perm("training.can_manage_library"))

        training_permission = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(TrainingSession),
            codename="can_manage_training",
        )
        user.user_permissions.add(training_permission)
        user = get_user_model().objects.get(pk=user.pk)
        self.assertTrue(user.has_perm("training.can_manage_training"))
        self.assertFalse(user.has_perm("training.can_manage_library"))
