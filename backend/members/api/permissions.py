"""
Custom permissions for email messaging system.
"""

from rest_framework import permissions


def sending_department_ids(user):
    """Departments where a role grants the email sending permission."""
    return user.department_roles.filter(
        groups__permissions__content_type__app_label="members",
        groups__permissions__codename="can_send_member_emails",
    ).values_list("department_id", flat=True)


class CanSendEmails(permissions.BasePermission):
    """
    Permission to check if user can send emails to members.

    Sending requires the explicit global or department role permission.
    """

    def has_permission(self, request, view):
        # Authenticated users only
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.has_perm("members.can_send_member_emails") or sending_department_ids(request.user).exists()
