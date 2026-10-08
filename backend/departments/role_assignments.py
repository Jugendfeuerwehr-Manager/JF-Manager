"""Authorization and review snapshots for explicit role assignments."""

import hashlib
import json

from rest_framework.exceptions import PermissionDenied

from departments.assignment_sources import effective_group_ids
from departments.delegation import delegation_approved, permission_names
from departments.models import Department, RoleGrant
from departments.role_comparison import compare_role_template
from users.mfa_policy import mfa_required

ASSIGN = "departments.can_assign_roles"
DELEGATE = "departments.can_delegate_roles"
LEADERSHIP = "departments.can_delegate_department_leadership"
ORG_SCOPE = "departments.can_access_all_departments"


def is_role_administrator(user):
    return user.is_active and user.has_perm(ASSIGN)


def scoped_permission(user, name, department_id):
    if not user.is_active:
        return False
    if user.has_perm(name):
        return user.has_perm(ORG_SCOPE) or user.department_roles.filter(department_id=department_id).exists()
    app, code = name.split(".")
    return user.department_roles.filter(
        department_id=department_id,
        groups__permissions__content_type__app_label=app,
        groups__permissions__codename=code,
    ).exists()


def assignable_departments(user):
    departments = Department.objects.filter(is_active=True)
    if is_role_administrator(user) or (user.has_perm(DELEGATE) and user.has_perm(ORG_SCOPE)):
        return departments
    return departments.filter(pk__in=[d.pk for d in departments if scoped_permission(user, DELEGATE, d.pk)])


def can_assign_template(actor, template, department_id, *, operation="add"):
    if not template.group_id or template.scope not in ("department", "organization"):
        return False
    if (department_id is None) != (template.scope == "organization"):
        return False
    if operation == "add" and template.is_archived:
        return False
    if is_role_administrator(actor):
        return True
    if department_id is None or not scoped_permission(actor, DELEGATE, department_id):
        return False
    if template.key == "department_youth_director":
        return actor.has_perm(LEADERSHIP) and actor.has_perm(ORG_SCOPE)
    return delegation_approved(template)


def authorize_assignment(actor, target, template, department_id, operation):
    if actor.pk == target.pk:
        raise PermissionDenied("Eigene Rollen dürfen nicht über die Zuweisung geändert werden.")
    if not target.is_active or target.username == "AnonymousUser":
        raise PermissionDenied("Nur aktive persönliche Konten können ausgewählt werden.")
    if not is_role_administrator(actor) and mfa_required(target):
        raise PermissionDenied("Privilegierte Konten werden ausschließlich administrativ verwaltet.")
    if department_id is not None and not assignable_departments(actor).filter(pk=department_id).exists():
        raise PermissionDenied("Keine Zuweisungsberechtigung für diese Abteilung.")
    if not can_assign_template(actor, template, department_id, operation=operation):
        raise PermissionDenied("Die Rolle ist für diesen Bereich nicht zur Zuweisung freigegeben.")


def assignment_preview(actor, target, template, department_id, operation):
    authorize_assignment(actor, target, template, department_id, operation)
    current = effective_group_ids(target, department_id)
    local = set(
        RoleGrant.objects.filter(user=target, department_id=department_id, source="local").values_list(
            "group_id", flat=True
        )
    )
    tracked = set(RoleGrant.objects.filter(user=target, department_id=department_id).values_list("group_id", flat=True))
    local |= current - tracked
    external = (
        RoleGrant.objects.filter(user=target, department_id=department_id, group=template.group)
        .exclude(source="local")
        .exists()
    )
    changed = template.group_id not in local if operation == "add" else template.group_id in local
    remains = operation == "remove" and external
    before = set()
    from django.contrib.auth.models import Group

    for group in Group.objects.filter(pk__in=current):
        before.update(permission_names(group))
    after_ids = (
        current | {template.group_id}
        if operation == "add"
        else current - ({template.group_id} if not external else set())
    )
    after = set()
    for group in Group.objects.filter(pk__in=after_ids):
        after.update(permission_names(group))
    snapshot = {
        "actor": actor.pk,
        "actor_global": sorted(actor.get_all_permissions()),
        "actor_scoped": list(
            actor.department_roles.order_by("pk").values_list("department_id", "groups__permissions__pk")
        ),
        "target": target.pk,
        "target_active": target.is_active,
        "target_staff": target.is_staff,
        "target_superuser": target.is_superuser,
        "target_global": sorted(target.get_all_permissions()),
        "target_scoped": list(
            target.department_roles.order_by("pk").values_list("department_id", "groups__permissions__pk")
        ),
        "department": department_id,
        "operation": operation,
        "template": compare_role_template(template)["fingerprint"],
        "current": sorted(current),
        "sources": list(
            RoleGrant.objects.filter(user=target)
            .order_by("pk")
            .values_list("pk", "group_id", "department_id", "source", "source_key")
        ),
        "before": sorted(before),
        "after": sorted(after),
    }
    return {
        "fingerprint": hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
        "person": {"id": target.pk, "name": target.get_full_name() or target.username},
        "role": {"id": template.pk, "name": template.name, "description": template.description},
        "department": {"id": department_id, "name": Department.objects.get(pk=department_id).name}
        if department_id
        else None,
        "operation": operation,
        "changed": changed,
        "retained_external": remains,
        "added_permissions": sorted(after - before),
        "removed_permissions": sorted(before - after),
        "permissions": sorted(after),
        "effect": (
            "Lokale Zuweisung hinzufügen."
            if operation == "add"
            else "Lokale Zuweisung entfernen; externe Zuweisung bleibt wirksam."
            if remains
            else "Lokale Zuweisung entfernen."
        ),
    }


def explain_roles(user, department_ids=None, *, include_global=True):
    from django.contrib.auth.models import Group

    areas = (
        list(user.department_roles.values_list("department_id", flat=True))
        if department_ids is None
        else list(department_ids)
    )
    if include_global:
        areas.append(None)
    rows = []
    for department_id in areas:
        for group in Group.objects.filter(pk__in=effective_group_ids(user, department_id)).select_related(
            "role_template"
        ):
            template = getattr(group, "role_template", None)
            sources = list(
                RoleGrant.objects.filter(user=user, department_id=department_id, group=group).values(
                    "source", "source_key"
                )
            )
            if not sources:
                sources = [{"source": "local", "source_key": ""}]
            rows.append(
                {
                    "role": template.name if template else group.name,
                    "template_id": template.pk if template else None,
                    "department_id": department_id,
                    "department": Department.objects.get(pk=department_id).name if department_id else "Organisation",
                    "sources": sources,
                    "permissions": permission_names(group),
                }
            )
    if include_global and user.user_permissions.exists():
        rows.append(
            {
                "role": "Direkt zugewiesene Berechtigungen",
                "template_id": None,
                "department_id": None,
                "department": "Organisation",
                "sources": [{"source": "local", "source_key": ""}],
                "permissions": sorted(user.get_user_permissions()),
            }
        )
    if include_global and user.is_superuser:
        rows.append(
            {
                "role": "Notfallkonto (Superuser)",
                "template_id": None,
                "department_id": None,
                "department": "Organisation",
                "sources": [{"source": "local", "source_key": ""}],
                "permissions": ["*"],
            }
        )
    return rows
