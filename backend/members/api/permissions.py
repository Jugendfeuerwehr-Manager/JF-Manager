"""
Custom permissions for email messaging system.
"""

from rest_framework import permissions


class CanSendEmails(permissions.BasePermission):
    """
    Permission to check if user can send emails to members.

    Staff users can always send emails.
    Non-staff users need the 'can_send_member_emails' permission.
    """

    def has_permission(self, request, view):
        # Authenticated users only
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff users can always send emails
        if request.user.is_staff:
            return True

        # Check for specific permission
        return request.user.has_perm('members.can_send_member_emails')
