"""Administrative approval binds delegation to the exact group permissions."""

import hashlib
import json

from departments.models import RoleTemplate
from users.mfa_policy import PRIVILEGED_PERMISSIONS


def permission_names(group):
    return sorted(f"{app}.{code}" for app, code in group.permissions.values_list("content_type__app_label", "codename"))


def approval_digest(template):
    if not template.group_id:
        return ""
    snapshot = [template.group_id, template.scope, permission_names(template.group)]
    return hashlib.sha256(json.dumps(snapshot, separators=(",", ":")).encode()).hexdigest()


def can_approve_delegation(template):
    if (
        not template.group_id
        or template.is_archived
        or not template.is_delegable
        or template.scope != RoleTemplate.Scope.DEPARTMENT
    ):
        return False
    names = set(permission_names(template.group))
    # Administrative, delegation and destructive rights must never be passed on
    # through an ordinary subordinate role, even after a raw group edit.
    return not any(
        name in PRIVILEGED_PERMISSIONS
        or name.startswith(("auth.", "users.", "settings_manager."))
        or name.split(".")[1].startswith(("delete_", "anonymize_"))
        or name == "departments.can_access_all_departments"
        for name in names
    )


def delegation_approved(template):
    return can_approve_delegation(template) and template.delegation_approval == approval_digest(template)
