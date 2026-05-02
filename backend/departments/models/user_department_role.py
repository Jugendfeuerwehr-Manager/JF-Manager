from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models

from .department import Department


class UserDepartmentRole(models.Model):
    """
    Assigns a user to a department with a set of Django Groups.
    Each group can carry arbitrary permissions, which apply only within
    the context of that department.

    Users with is_staff=True or the departments.can_access_all_departments
    permission bypass this table and see all data.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="department_roles",
        verbose_name="Benutzer",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name="Abteilung",
    )
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="department_assignments",
        verbose_name="Gruppen",
    )

    class Meta:
        verbose_name = "Benutzer-Abteilung-Zuordnung"
        verbose_name_plural = "Benutzer-Abteilung-Zuordnungen"
        unique_together = [["user", "department"]]

    def __str__(self):
        return f"{self.user} → {self.department}"
