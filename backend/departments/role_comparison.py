"""Read-only permission comparison for role administration."""

import hashlib
import json

from departments.role_catalog import ROLE_SPECS

SPECS_BY_KEY = {spec.key: spec for spec in ROLE_SPECS}


def compare_role_template(template):
    group = template.group
    actual = (
        sorted(f"{permission.content_type.app_label}.{permission.codename}" for permission in group.permissions.all())
        if group
        else []
    )
    spec = SPECS_BY_KEY.get(template.key)
    expected = sorted(spec.permissions) if spec else None
    expected_metadata = (
        {
            "name": spec.name,
            "description": spec.description,
            "template_version": spec.version,
            "scope": spec.scope,
            "is_delegable": spec.is_delegable,
            "is_archived": False,
            "group_name": spec.group_name,
        }
        if spec
        else None
    )
    actual_metadata = {
        "name": template.name,
        "description": template.description,
        "template_version": template.template_version,
        "scope": template.scope,
        "is_delegable": template.is_delegable,
        "is_archived": template.is_archived,
        "group_name": group.name if group else None,
    }
    actual_set = set(actual)
    expected_set = set(expected) if expected is not None else None
    assignments = {
        "global_users": group.user_set.count() if group else 0,
        "staff_users": group.user_set.filter(is_staff=True).count() if group else 0,
        "department_roles": group.department_assignments.count() if group else 0,
        "ldap_mappings": group.ldap_role_mappings.count() if group else 0,
        "oidc_mappings": group.oidc_group_mappings.count() if group else 0,
    }
    snapshot = {
        "template_id": template.pk,
        "key": template.key,
        "name": template.name,
        "description": template.description,
        "template_version": template.template_version,
        "scope": template.scope,
        "is_delegable": template.is_delegable,
        "is_archived": template.is_archived,
        "group_id": template.group_id,
        "group_name": group.name if group else None,
        "updated_at": template.updated_at.isoformat(),
        "actual_permission_ids": sorted(group.permissions.values_list("pk", flat=True)) if group else [],
        "actual_permissions": actual,
        "expected_permissions": expected,
        "expected_metadata": expected_metadata,
        "global_user_ids": sorted(group.user_set.values_list("pk", flat=True)) if group else [],
        "staff_user_ids": sorted(group.user_set.filter(is_staff=True).values_list("pk", flat=True)) if group else [],
        "department_assignments": (
            sorted(group.department_assignments.values_list("pk", "user_id", "department_id")) if group else []
        ),
        "ldap_mappings": sorted(group.ldap_role_mappings.values_list("pk", "department_id")) if group else [],
        "oidc_mappings": sorted(group.oidc_group_mappings.values_list("pk", "department_id")) if group else [],
    }
    fingerprint = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "actual_permissions": actual,
        "expected_permissions": expected,
        "expected_metadata": expected_metadata,
        "metadata_differences": (
            {
                field: {"actual": actual_metadata[field], "expected": wanted}
                for field, wanted in expected_metadata.items()
                if actual_metadata[field] != wanted
            }
            if expected_metadata is not None
            else None
        ),
        "missing_permissions": sorted(expected_set - actual_set) if expected_set is not None else None,
        "extra_permissions": sorted(actual_set - expected_set) if expected_set is not None else None,
        "assignment_counts": assignments,
        "fingerprint": fingerprint,
    }
